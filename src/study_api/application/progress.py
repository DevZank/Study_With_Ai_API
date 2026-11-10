"""Casos de uso de flashcards, revisão espaçada FSRS, métricas pedagógicas e gamificação."""

from study_api.application.chat import ChatService
from study_api.application.trail_service import TrailService
from study_api.domain.chat import AppError, now
from study_api.domain.content import FlashcardBlock, PublicDocument
from study_api.domain.progress import (
    DAILY_REVIEW_XP_CAP,
    DEFAULT_ACHIEVEMENTS,
    AchievementDefinition,
    Concept,
    ConceptMastery,
    EarnedAchievement,
    Flashcard,
    ProgressPreference,
    ProgressRecord,
    ProgressRepository,
    Rating,
    ReviewEvent,
    ReviewState,
    XpEvent,
    calculate_concept_mastery,
    concept_slug,
    format_utc,
    level_progress,
    parse_utc,
    retrievability_at,
    schedule_review,
)
from study_api.domain.trails import ContentVersion, Module, Trail, Unit

PREFERENCE_ID = "00000000-0000-0000-0000-000000000002"


class ProgressService:
    def __init__(
        self,
        repo: ProgressRepository,
        chat: ChatService,
        trails: TrailService,
    ) -> None:
        self.repo = repo
        self.chat = chat
        self.trails = trails

    def _active_topic(self, topic_id: str, write: bool = False) -> None:
        topic = self.chat.topic(topic_id)
        if write and topic.status != "active":
            raise AppError(
                "TOPIC_ARCHIVED",
                "Restaure o tema arquivado antes de registrar alterações.",
                409,
            )

    def _ensure_concept(
        self,
        topic_id: str,
        name: str,
        source_type: str = "manual",
        definition: str = "",
    ) -> Concept:
        clean_name = (name.strip() or "Conceito geral")[:160]
        slug = concept_slug(clean_name)
        existing = [
            c for c in self.repo.all(Concept, ("topic_id", topic_id)) if c.slug == slug
        ]
        if existing:
            return existing[0]
        allowed_source = (
            source_type
            if source_type in {"trail", "exercise", "flashcard", "manual"}
            else "manual"
        )
        concept = Concept(
            topic_id=topic_id,
            slug=slug,
            name=clean_name,
            definition=definition[:400],
            source_type=allowed_source,  # type: ignore[arg-type]
        )
        self.repo.commit([concept])
        return concept

    def create_flashcard(
        self,
        topic_id: str,
        front: str,
        back: str,
        concept_name: str,
        operation_id: str,
        source_type: str = "manual",
        source_ref: dict[str, object] | None = None,
        source_key: str | None = None,
        created_at: str | None = None,
    ) -> tuple[Flashcard, ReviewState]:
        self._active_topic(topic_id, write=True)
        clean_front = front.strip()
        clean_back = back.strip()
        clean_concept = (concept_name.strip() or self.chat.topic(topic_id).title)[:160]

        by_op = self.repo.find_by(Flashcard, "operation_id", operation_id)
        if by_op is not None:
            if (
                by_op.topic_id != topic_id
                or by_op.front != clean_front
                or by_op.back != clean_back
            ):
                raise AppError(
                    "IDEMPOTENCY_CONFLICT",
                    "Identificador de operação já usado com outro cartão.",
                    409,
                )
            state = self.review_state(by_op.id)
            return by_op, state

        if source_key:
            by_source = self.repo.find_by(Flashcard, "source_key", source_key)
            if by_source is not None:
                return by_source, self.review_state(by_source.id)

        concept = self._ensure_concept(
            topic_id,
            clean_concept,
            "flashcard",
        )
        timestamp = format_utc(parse_utc(created_at)) if created_at else now()
        allowed_source = (
            source_type
            if source_type in {"manual", "message_block", "notebook_page"}
            else "manual"
        )
        card = Flashcard(
            topic_id=topic_id,
            concept_id=concept.id,
            concept_name=concept.name,
            front=clean_front,
            back=clean_back,
            source_type=allowed_source,  # type: ignore[arg-type]
            source_ref=source_ref or {},  # type: ignore[arg-type]
            source_key=source_key,
            operation_id=operation_id,
            created_at=timestamp,
            updated_at=timestamp,
        )
        state = ReviewState(
            flashcard_id=card.id,
            topic_id=topic_id,
            due_at=timestamp,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.repo.commit([card, state])
        self.sync_topic(topic_id)
        return card, state

    def import_from_message(
        self,
        message_id: str,
        block_id: str,
        concept_name: str,
        operation_id: str,
    ) -> tuple[Flashcard, ReviewState]:
        message = self.chat.get_message(message_id)
        conversation = self.chat.conversation(message.conversation_id)
        topic = self.chat.topic(conversation.topic_id)
        if topic.status != "active":
            raise AppError(
                "TOPIC_ARCHIVED",
                "Restaure o tema antes de salvar cartões na fila.",
                409,
            )
        if (
            message.role != "assistant"
            or message.status != "completed"
            or not message.document_json
        ):
            raise AppError(
                "INVALID_FLASHCARD_SOURCE",
                "Apenas respostas estruturadas concluídas permitem importar cartões.",
                409,
            )
        document = PublicDocument.model_validate_json(message.document_json)
        block = next(
            (
                b
                for b in document.blocks
                if isinstance(b, FlashcardBlock) and b.id == block_id
            ),
            None,
        )
        if block is None:
            raise AppError(
                "NOT_FOUND",
                "Bloco de flashcard não encontrado nesta resposta.",
                404,
            )
        source_ref: dict[str, object] = {
            "topic_id": topic.id,
            "conversation_id": conversation.id,
            "message_id": message.id,
            "block_id": block.id,
            "model_id": message.model_id,
            "document_title": document.title,
        }
        for version in self.trails.repo.all(ContentVersion, ("message_id", message.id)):
            unit = self.trails.repo.get(Unit, version.unit_id)
            module = self.trails.repo.get(Module, unit.module_id)
            source_ref.update(
                trail_id=module.trail_id,
                module_id=module.id,
                unit_id=unit.id,
                content_version_id=version.id,
            )
        resolved_concept = concept_name.strip() or document.title
        return self.create_flashcard(
            topic_id=topic.id,
            front=block.front,
            back=block.back,
            concept_name=resolved_concept,
            operation_id=operation_id,
            source_type="message_block",
            source_ref=source_ref,
            source_key=f"msg:{message.id}:{block.id}",
        )

    def edit_flashcard(
        self,
        flashcard_id: str,
        front: str,
        back: str,
        concept_name: str,
        archived: bool,
        expected_version: int,
        operation_id: str,
    ) -> tuple[Flashcard, ReviewState]:
        card = self.repo.get(Flashcard, flashcard_id)
        self._active_topic(card.topic_id, write=True)
        clean_front = front.strip()
        clean_back = back.strip()
        clean_concept = (concept_name.strip() or card.concept_name)[:160]

        if card.operation_id == operation_id:
            if (
                card.front == clean_front
                and card.back == clean_back
                and card.concept_name == clean_concept
                and card.archived == archived
            ):
                return card, self.review_state(card.id)
            raise AppError(
                "IDEMPOTENCY_CONFLICT",
                "Identificador de operação já utilizado com outra edição.",
                409,
            )
        if card.version != expected_version:
            raise AppError(
                "FLASHCARD_CONFLICT",
                "O cartão mudou. Recarregue antes de salvar.",
                409,
            )

        concept = self._ensure_concept(card.topic_id, clean_concept, "flashcard")
        updated = card.model_copy(
            update={
                "front": clean_front,
                "back": clean_back,
                "concept_id": concept.id,
                "concept_name": concept.name,
                "archived": archived,
                "version": expected_version + 1,
                "operation_id": operation_id,
            }
        )
        self.repo.commit([updated], guard=(Flashcard, card.id, expected_version))
        self.sync_topic(card.topic_id)
        return updated, self.review_state(card.id)

    def review_state(self, flashcard_id: str) -> ReviewState:
        state = self.repo.find_by(ReviewState, "flashcard_id", flashcard_id)
        if state is None:
            raise AppError("NOT_FOUND", "Estado de revisão não encontrado.", 404)
        return state

    def review_history(self, flashcard_id: str) -> list[ReviewEvent]:
        card = self.repo.get(Flashcard, flashcard_id)
        self._active_topic(card.topic_id, write=False)
        return self.repo.all(ReviewEvent, ("flashcard_id", flashcard_id))

    def list_flashcards(
        self,
        topic_id: str,
        include_archived: bool = False,
        at_time: str | None = None,
    ) -> list[tuple[Flashcard, ReviewState, float | None, bool]]:
        self._active_topic(topic_id, write=False)
        ref_time = format_utc(parse_utc(at_time)) if at_time else now()
        ref_dt = parse_utc(ref_time)
        cards = self.repo.all(Flashcard, ("topic_id", topic_id))
        states = {
            s.flashcard_id: s
            for s in self.repo.all(ReviewState, ("topic_id", topic_id))
        }
        items: list[tuple[Flashcard, ReviewState, float | None, bool]] = []
        for card in cards:
            if card.archived and not include_archived:
                continue
            state = states.get(card.id) or self.review_state(card.id)
            retention = retrievability_at(state, ref_time)
            due = not card.archived and parse_utc(state.due_at) <= ref_dt
            items.append((card, state, retention, due))
        return items

    def due_reviews(
        self,
        topic_id: str | None = None,
        at_time: str | None = None,
        limit: int = 50,
    ) -> list[tuple[Flashcard, ReviewState, float | None]]:
        ref_time = format_utc(parse_utc(at_time)) if at_time else now()
        ref_dt = parse_utc(ref_time)
        if topic_id:
            self._active_topic(topic_id, write=False)
            if self.chat.topic(topic_id).status != "active":
                return []
            states = self.repo.all(ReviewState, ("topic_id", topic_id))
            cards = {c.id: c for c in self.repo.all(Flashcard, ("topic_id", topic_id))}
        else:
            active_topics = {
                t.id for t in self.chat.repo.topics() if t.status == "active"
            }
            states = [
                s for s in self.repo.all(ReviewState) if s.topic_id in active_topics
            ]
            cards = {
                c.id: c for c in self.repo.all(Flashcard) if c.topic_id in active_topics
            }

        due_list: list[tuple[Flashcard, ReviewState, float | None]] = []
        for state in states:
            card = cards.get(state.flashcard_id)
            if card is None or card.archived:
                continue
            if parse_utc(state.due_at) <= ref_dt:
                due_list.append((card, state, retrievability_at(state, ref_time)))
        due_list.sort(key=lambda item: (item[1].due_at, item[0].created_at, item[0].id))
        return due_list[:limit]

    def grade_review(
        self,
        flashcard_id: str,
        rating: Rating,
        request_id: str,
        reviewed_at: str | None = None,
    ) -> tuple[Flashcard, ReviewState, ReviewEvent]:
        existing_event = self.repo.find_by(ReviewEvent, "request_id", request_id)
        if existing_event is not None:
            if (
                existing_event.flashcard_id != flashcard_id
                or existing_event.rating != rating
            ):
                raise AppError(
                    "IDEMPOTENCY_CONFLICT",
                    "Identificador de revisão já utilizado com outros parâmetros.",
                    409,
                )
            card = self.repo.get(Flashcard, flashcard_id)
            return card, self.review_state(flashcard_id), existing_event

        card = self.repo.get(Flashcard, flashcard_id)
        self._active_topic(card.topic_id, write=True)
        if card.archived:
            raise AppError(
                "CARD_ARCHIVED",
                "Restaure o cartão arquivado antes de registrar revisão.",
                409,
            )
        state = self.review_state(card.id)
        ref_time = format_utc(parse_utc(reviewed_at)) if reviewed_at else now()
        if state.last_reviewed_at and parse_utc(ref_time) < parse_utc(
            state.last_reviewed_at
        ):
            raise AppError(
                "INVALID_REVIEW_TIME",
                "O horário da revisão não pode ser anterior à última revisão do cartão.",
                422,
            )

        updated_state, event = schedule_review(state, rating, ref_time, request_id)
        records: list[ProgressRecord] = [updated_state, event]

        # Proteção anti-farming: XP apenas para cartões efetivamente vencidos,
        # no máximo uma vez por cartão por dia UTC e respeitando teto diário.
        day_bucket = ref_time[:10]
        source_key = f"review_due:{card.id}:{day_bucket}"
        if (
            event.was_due
            and self.repo.find_by(XpEvent, "source_key", source_key) is None
        ):
            daily_reviews = [
                x
                for x in self.repo.all(XpEvent)
                if x.source_type == "flashcard_review"
                and x.source_key.endswith(f":{day_bucket}")
            ]
            if len(daily_reviews) < DAILY_REVIEW_XP_CAP:
                event.xp_awarded = 10
                records.append(
                    XpEvent(
                        topic_id=card.topic_id,
                        source_type="flashcard_review",
                        source_id=event.id,
                        source_key=source_key,
                        points=10,
                        reason=f"Revisão FSRS no prazo: {card.concept_name}",
                        created_at=ref_time,
                        updated_at=ref_time,
                    )
                )

        self.repo.commit(
            records,
            guard=(ReviewState, state.id, state.version),
        )
        self.sync_topic(card.topic_id)
        return card, updated_state, event

    def _ensure_achievements(self) -> list[AchievementDefinition]:
        existing = {a.code: a for a in self.repo.all(AchievementDefinition)}
        to_create: list[ProgressRecord] = []
        for code, title, description, rule in DEFAULT_ACHIEVEMENTS:
            if code not in existing:
                item = AchievementDefinition(
                    code=code,
                    title=title,
                    description=description,
                    rule=rule,
                )
                existing[code] = item
                to_create.append(item)
        if to_create:
            self.repo.commit(to_create)
        return [existing[code] for code, _, _, _ in DEFAULT_ACHIEVEMENTS]

    def _award_xp_if_absent(
        self,
        topic_id: str,
        source_type: str,
        source_id: str,
        source_key: str,
        points: int,
        reason: str,
    ) -> None:
        if self.repo.find_by(XpEvent, "source_key", source_key) is not None:
            return
        event = XpEvent(
            topic_id=topic_id,
            source_type=source_type,  # type: ignore[arg-type]
            source_id=source_id,
            source_key=source_key,
            points=points,
            reason=reason,
        )
        self.repo.commit([event])

    def sync_topic(self, topic_id: str) -> None:
        """Sincroniza conceitos, domínio estimado, XP determinístico e conquistas a partir de eventos reais."""
        topic = self.chat.repo.topic(topic_id)
        if topic.status == "deleted":
            return

        # 1. Conceitos e XP de unidades concluídas nas trilhas do tema.
        version_concepts: dict[str, list[str]] = {}
        for trail in self.trails.repo.all(Trail, ("topic_id", topic_id)):
            for module in self.trails.modules(trail.id):
                if module.archived:
                    continue
                for unit in self.trails.units(module.id):
                    versions = self.trails.versions(unit.id)
                    unit_completed = False
                    for version in versions:
                        summaries = self.trails.summaries(version.id)
                        if summaries:
                            unit_completed = True
                            names = list(summaries[-1].content.concepts)
                            version_concepts[version.message_id] = names
                            for name in names:
                                self._ensure_concept(topic_id, name, "trail")
                        else:
                            version_concepts[version.message_id] = [unit.title]
                    if unit_completed:
                        self._award_xp_if_absent(
                            topic_id=topic_id,
                            source_type="unit_completion",
                            source_id=unit.id,
                            source_key=f"unit_complete:{unit.id}",
                            points=25,
                            reason=f"Unidade de trilha concluída: {unit.title}",
                        )

        # 2. Tentativas de exercícios em conversas livres e unidades da trilha.
        concept_scores: dict[str, list[tuple[float, str]]] = {}
        for conv in self.chat.repo.conversations(topic_id):
            for msg in self.chat.repo.messages(conv.id):
                if (
                    msg.role != "assistant"
                    or msg.status != "completed"
                    or not msg.document_json
                ):
                    continue
                try:
                    doc = PublicDocument.model_validate_json(msg.document_json)
                except ValueError:
                    continue
                linked_names = version_concepts.get(msg.id) or [doc.title]
                for block in doc.blocks:
                    if block.type not in ("quiz", "exercise"):
                        continue
                    attempts = self.chat.repo.attempts(block.exercise_id)
                    if not attempts:
                        continue
                    self._award_xp_if_absent(
                        topic_id=topic_id,
                        source_type="exercise_first_try",
                        source_id=block.exercise_id,
                        source_key=f"exercise_first_try:{block.exercise_id}",
                        points=5,
                        reason=f"Primeira tentativa registrada em exercício: {doc.title}",
                    )
                    if any(a.score == 1.0 for a in attempts):
                        self._award_xp_if_absent(
                            topic_id=topic_id,
                            source_type="exercise_correct",
                            source_id=block.exercise_id,
                            source_key=f"exercise_correct:{block.exercise_id}",
                            points=15,
                            reason=f"Exercício objetivo resolvido de acordo com o gabarito: {doc.title}",
                        )
                    objective = [
                        (float(a.score), a.created_at)
                        for a in attempts
                        if a.score is not None
                    ]
                    for name in linked_names:
                        concept = self._ensure_concept(topic_id, name, "exercise")
                        concept_scores.setdefault(concept.id, []).extend(objective)

        # 3. Revisões FSRS associadas aos conceitos dos flashcards.
        concept_reviews: dict[str, list[tuple[Rating, str]]] = {}
        cards = {
            c.id: c
            for c in self.repo.all(Flashcard, ("topic_id", topic_id))
            if not c.archived
        }
        for card in cards.values():
            concept = (
                self.repo.get(Concept, card.concept_id)
                if card.concept_id
                else self._ensure_concept(topic_id, card.concept_name, "flashcard")
            )
            events = self.repo.all(ReviewEvent, ("flashcard_id", card.id))
            concept_reviews.setdefault(concept.id, []).extend(
                (e.rating, e.reviewed_at) for e in events
            )

        # 4. Atualiza registros de ConceptMastery do tema.
        existing_mastery = {
            m.concept_id: m
            for m in self.repo.all(ConceptMastery, ("topic_id", topic_id))
        }
        mastery_records: list[ProgressRecord] = []
        for concept in self.repo.all(Concept, ("topic_id", topic_id)):
            computed = calculate_concept_mastery(
                concept,
                concept_scores.get(concept.id, []),
                concept_reviews.get(concept.id, []),
            )
            prior = existing_mastery.get(concept.id)
            if prior is not None:
                computed = computed.model_copy(
                    update={
                        "id": prior.id,
                        "created_at": prior.created_at,
                        "version": prior.version + 1,
                    }
                )
            mastery_records.append(computed)
        if mastery_records:
            self.repo.commit(mastery_records)

        self._evaluate_achievements()

    def sync_all(self) -> None:
        self._ensure_achievements()
        for topic in self.chat.repo.topics():
            if topic.status != "deleted":
                self.sync_topic(topic.id)
        self._evaluate_achievements()

    def _evaluate_achievements(self) -> None:
        definitions = self._ensure_achievements()
        earned_codes = {e.code for e in self.repo.all(EarnedAchievement)}
        xp_events = self.repo.all(XpEvent)
        review_events = self.repo.all(ReviewEvent)

        practice_topics = {
            x.topic_id
            for x in xp_events
            if x.source_type == "exercise_first_try" and x.topic_id
        }
        review_topics = {
            self.repo.get(Flashcard, r.flashcard_id).topic_id for r in review_events
        }
        metrics = {
            "exercise_attempts": sum(
                1 for x in xp_events if x.source_type == "exercise_first_try"
            ),
            "correct_exercises": sum(
                1 for x in xp_events if x.source_type == "exercise_correct"
            ),
            "review_events": len(review_events),
            "completed_units": sum(
                1 for x in xp_events if x.source_type == "unit_completion"
            ),
            "combined_practice_and_review": len(practice_topics & review_topics),
        }

        new_earned: list[ProgressRecord] = []
        for definition in definitions:
            if definition.code in earned_codes:
                continue
            metric_name = str(definition.rule.get("metric", ""))
            minimum = int(str(definition.rule.get("min", 1)))
            if metrics.get(metric_name, 0) >= minimum:
                new_earned.append(
                    EarnedAchievement(
                        achievement_id=definition.id,
                        code=definition.code,
                        title=definition.title,
                        description=definition.description,
                    )
                )
        if new_earned:
            self.repo.commit(new_earned)

    def preference(self) -> ProgressPreference:
        rows = self.repo.all(ProgressPreference)
        if rows:
            return rows[0]
        default = ProgressPreference(id=PREFERENCE_ID, hide_gamification=False)
        self.repo.commit([default])
        return default

    def set_preference(self, hide_gamification: bool) -> ProgressPreference:
        current = self.preference()
        updated = current.model_copy(
            update={
                "hide_gamification": hide_gamification,
                "version": current.version + 1,
            }
        )
        self.repo.commit([updated])
        return updated

    def gamification_summary(self) -> dict[str, object]:
        pref = self.preference()
        definitions = self._ensure_achievements()
        earned = {e.code: e for e in self.repo.all(EarnedAchievement)}
        xp_events = self.repo.all(XpEvent)
        total_xp = sum(x.points for x in xp_events)
        lvl = level_progress(total_xp)
        return {
            **lvl,
            "hide_gamification": pref.hide_gamification,
            "anti_farming_policy": (
                "Recompensas determinísticas apenas por ações válidas únicas "
                "(primeira tentativa e resolução de exercício, conclusão de unidade "
                "e revisão FSRS de cartão efetivamente vencido, até 30 revisões premiadas/dia). "
                "Repetir respostas ou enviar mensagens não gera XP extra."
            ),
            "recent_xp_events": list(reversed(xp_events[-15:])),
            "achievements": [
                {
                    "code": d.code,
                    "title": d.title,
                    "description": d.description,
                    "earned": d.code in earned,
                    "earned_at": earned[d.code].earned_at if d.code in earned else None,
                }
                for d in definitions
            ],
        }

    def topic_progress(
        self, topic_id: str, at_time: str | None = None
    ) -> dict[str, object]:
        self._active_topic(topic_id, write=False)
        self.sync_topic(topic_id)
        ref_time = format_utc(parse_utc(at_time)) if at_time else now()
        ref_dt = parse_utc(ref_time)

        # Indicador 1: Conclusão de atividades (trilhas e unidades)
        trail_progress: list[dict[str, object]] = []
        total_units_all = 0
        completed_units_all = 0
        generated_units_all = 0
        for trail in self.trails.repo.all(Trail, ("topic_id", topic_id)):
            t_total = 0
            t_completed = 0
            t_generated = 0
            for module in self.trails.modules(trail.id):
                if module.archived:
                    continue
                for unit in self.trails.units(module.id):
                    t_total += 1
                    versions = self.trails.versions(unit.id)
                    if versions:
                        t_generated += 1
                        if self.trails.summaries(versions[-1].id):
                            t_completed += 1
            total_units_all += t_total
            completed_units_all += t_completed
            generated_units_all += t_generated
            trail_progress.append(
                {
                    "trail_id": trail.id,
                    "title": trail.title,
                    "completed_units": t_completed,
                    "generated_units": t_generated,
                    "total_units": t_total,
                    "completion_ratio": (
                        round(t_completed / t_total, 4) if t_total > 0 else None
                    ),
                }
            )

        # Indicador 2: Domínio estimado por conceito (evidências de prática/revisão)
        mastery_rows = sorted(
            self.repo.all(ConceptMastery, ("topic_id", topic_id)),
            key=lambda m: (m.concept_name.casefold(), m.id),
        )
        scored_concepts = [m.score for m in mastery_rows if m.score is not None]
        average_mastery = (
            round(sum(scored_concepts) / len(scored_concepts), 4)
            if scored_concepts
            else None
        )

        # Indicador 3: Retenção estimada (curva FSRS dos cartões revisados)
        cards = [
            c
            for c in self.repo.all(Flashcard, ("topic_id", topic_id))
            if not c.archived
        ]
        states = {
            s.flashcard_id: s
            for s in self.repo.all(ReviewState, ("topic_id", topic_id))
        }
        retentions: list[float] = []
        due_count = 0
        reviewed_cards = 0
        for card in cards:
            state = states.get(card.id)
            if state is None:
                continue
            if parse_utc(state.due_at) <= ref_dt:
                due_count += 1
            r = retrievability_at(state, ref_time)
            if r is not None:
                reviewed_cards += 1
                retentions.append(r)
        average_retention = (
            round(sum(retentions) / len(retentions), 4) if retentions else None
        )

        # Recomendações adaptativas determinísticas (usuário sempre decide)
        recommendations: list[dict[str, str]] = []
        if due_count > 0:
            recommendations.append(
                {
                    "kind": "review_due",
                    "title": f"Revisar {due_count} cartão(ões) vencido(s)",
                    "description": (
                        "Há cartões de memorização aguardando revisão espaçada neste tema. "
                        "A revisão mantém a estabilidade FSRS atualizada."
                    ),
                }
            )
        low_mastery = [m for m in mastery_rows if m.score is not None and m.score < 0.6]
        if low_mastery:
            names = ", ".join(m.concept_name for m in low_mastery[:3])
            recommendations.append(
                {
                    "kind": "practice_concept",
                    "title": f"Reforçar prática em: {names}",
                    "description": (
                        "O desempenho observado nas tentativas recentes ficou abaixo de 60%. "
                        "Experimente o modo Praticar ou Estudar para revisar erros recorrentes."
                    ),
                }
            )
        if not cards:
            recommendations.append(
                {
                    "kind": "create_flashcards",
                    "title": "Adicionar cartões de revisão espaçada",
                    "description": (
                        "Crie cartões manualmente ou importe cartões gerados no modo Memorizar "
                        "para acompanhar a retenção estimada ao longo do tempo."
                    ),
                }
            )
        if total_units_all > completed_units_all:
            recommendations.append(
                {
                    "kind": "advance_trail",
                    "title": "Avançar para a próxima unidade da trilha",
                    "description": (
                        f"Você concluiu {completed_units_all} de {total_units_all} unidade(s) "
                        "ativas nas trilhas deste tema. Gere ou conclua a próxima quando desejar."
                    ),
                }
            )
        if not recommendations:
            recommendations.append(
                {
                    "kind": "keep_pace",
                    "title": "Indicadores em dia neste tema",
                    "description": (
                        "Nenhuma revisão vencida ou dificuldade recorrente detectada. "
                        "Você decide quando aprofundar ou iniciar um novo objetivo."
                    ),
                }
            )

        return {
            "topic_id": topic_id,
            "calculated_at": ref_time,
            "completion": {
                "trails": trail_progress,
                "completed_units": completed_units_all,
                "generated_units": generated_units_all,
                "total_units": total_units_all,
                "completion_ratio": (
                    round(completed_units_all / total_units_all, 4)
                    if total_units_all > 0
                    else None
                ),
            },
            "mastery": {
                "estimated_score": average_mastery,
                "evaluated_concepts": len(scored_concepts),
                "total_concepts": len(mastery_rows),
                "concepts": mastery_rows,
            },
            "retention": {
                "estimated_retention": average_retention,
                "active_cards": len(cards),
                "reviewed_cards": reviewed_cards,
                "due_cards": due_count,
            },
            "explanations": {
                "completion": (
                    "Progresso de atividades: mede exclusivamente quantas unidades ativas de "
                    "trilhas possuem resumo de conclusão registrado. Não mede acerto nem memória."
                ),
                "mastery": (
                    "Domínio estimado: calculado a partir de tentativas objetivas de exercícios "
                    "(peso 1,0) e revisões FSRS (peso 0,6) por conceito. É uma estimativa sujeita "
                    "a incerteza e erros de gabarito da IA, não uma certificação de conhecimento."
                ),
                "retention": (
                    "Retenção estimada: probabilidade média atual de recordação calculada pela "
                    "curva de esquecimento FSRS em função do tempo decorrido e da estabilidade "
                    "de cada cartão já revisado. Não se confunde com domínio de exercícios."
                ),
            },
            "recommendations": recommendations,
            "gamification": self.gamification_summary(),
        }

    def overview(self, at_time: str | None = None) -> dict[str, object]:
        self.sync_all()
        ref_time = format_utc(parse_utc(at_time)) if at_time else now()
        due = self.due_reviews(at_time=ref_time, limit=50)
        active_topics = [t for t in self.chat.repo.topics() if t.status == "active"]
        return {
            "calculated_at": ref_time,
            "due_count": len(due),
            "active_topics_count": len(active_topics),
            "gamification": self.gamification_summary(),
        }
