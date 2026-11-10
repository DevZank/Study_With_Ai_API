"""Persistência SQLite de flashcards, estados FSRS, métricas pedagógicas e gamificação."""

from sqlalchemy import Engine, ForeignKey, String, Text, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from study_api.domain.chat import LOCAL_PROFILE_ID, AppError, now
from study_api.domain.progress import (
    AchievementDefinition,
    Concept,
    ConceptMastery,
    EarnedAchievement,
    Flashcard,
    P,
    ProgressPreference,
    ProgressRecord,
    ReviewEvent,
    ReviewState,
    XpEvent,
)
from study_api.infrastructure.db.models import Base, Record


class ProgressData(Record, Base):
    __abstract__ = True
    version: Mapped[int]
    data_json: Mapped[str] = mapped_column(Text)


class ConceptRow(ProgressData):
    __tablename__ = "concepts"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    slug: Mapped[str] = mapped_column(String(120))


class ConceptMasteryRow(ProgressData):
    __tablename__ = "concept_mastery"
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"), unique=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)


class FlashcardRow(ProgressData):
    __tablename__ = "flashcards"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    concept_id: Mapped[str | None] = mapped_column(ForeignKey("concepts.id"))
    source_key: Mapped[str | None] = mapped_column(String(120), unique=True)
    operation_id: Mapped[str] = mapped_column(String(36), unique=True)


class ReviewStateRow(ProgressData):
    __tablename__ = "review_states"
    flashcard_id: Mapped[str] = mapped_column(ForeignKey("flashcards.id"), unique=True)
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    due_at: Mapped[str] = mapped_column(String(40), index=True)


class ReviewEventRow(ProgressData):
    __tablename__ = "review_events"
    review_state_id: Mapped[str] = mapped_column(
        ForeignKey("review_states.id"), index=True
    )
    flashcard_id: Mapped[str] = mapped_column(ForeignKey("flashcards.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)


class XpEventRow(ProgressData):
    __tablename__ = "xp_events"
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id"), index=True)
    source_key: Mapped[str] = mapped_column(String(120), unique=True)


class AchievementRow(ProgressData):
    __tablename__ = "achievements"
    code: Mapped[str] = mapped_column(String(64), unique=True)


class EarnedAchievementRow(ProgressData):
    __tablename__ = "earned_achievements"
    achievement_id: Mapped[str] = mapped_column(
        ForeignKey("achievements.id"), unique=True
    )
    code: Mapped[str] = mapped_column(String(64), unique=True)


class ProgressPreferenceRow(ProgressData):
    __tablename__ = "progress_preferences"


MAPPING: dict[type[ProgressRecord], type[ProgressData]] = {
    Concept: ConceptRow,
    ConceptMastery: ConceptMasteryRow,
    Flashcard: FlashcardRow,
    ReviewState: ReviewStateRow,
    ReviewEvent: ReviewEventRow,
    XpEvent: XpEventRow,
    AchievementDefinition: AchievementRow,
    EarnedAchievement: EarnedAchievementRow,
    ProgressPreference: ProgressPreferenceRow,
}

FIELDS: dict[type[ProgressRecord], list[str]] = {
    Concept: ["topic_id", "slug"],
    ConceptMastery: ["concept_id", "topic_id"],
    Flashcard: ["topic_id", "concept_id", "source_key", "operation_id"],
    ReviewState: ["flashcard_id", "topic_id", "due_at"],
    ReviewEvent: ["review_state_id", "flashcard_id", "request_id"],
    XpEvent: ["topic_id", "source_key"],
    AchievementDefinition: ["code"],
    EarnedAchievement: ["achievement_id", "code"],
    ProgressPreference: [],
}


class SqliteProgress:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, cls: type[P], record_id: str) -> P:
        with Session(self.engine) as session:
            row = session.get(MAPPING[cls], record_id)
            if row is None or row.owner_id != LOCAL_PROFILE_ID:
                raise AppError(
                    "NOT_FOUND", "Registro de progresso não encontrado.", 404
                )
            return cls.model_validate_json(row.data_json)

    def find_by(self, cls: type[P], field: str, value: str) -> P | None:
        if field not in FIELDS[cls]:
            raise ValueError("Campo de busca não permitido no repositório.")
        with Session(self.engine) as session:
            row_cls = MAPPING[cls]
            query = select(row_cls).where(
                row_cls.owner_id == LOCAL_PROFILE_ID,
                getattr(row_cls, field) == value,
            )
            found = session.scalars(query).first()
            return cls.model_validate_json(found.data_json) if found else None

    def all(
        self,
        cls: type[P],
        parent: tuple[str, str] | None = None,
    ) -> list[P]:
        with Session(self.engine) as session:
            row_cls = MAPPING[cls]
            query = select(row_cls).where(row_cls.owner_id == LOCAL_PROFILE_ID)
            if parent:
                if parent[0] not in FIELDS[cls]:
                    raise ValueError("Filtro não permitido no repositório.")
                query = query.where(getattr(row_cls, parent[0]) == parent[1])
            query = query.order_by(row_cls.created_at, row_cls.id)
            return [
                cls.model_validate_json(r.data_json) for r in session.scalars(query)
            ]

    def commit(
        self,
        records: list[ProgressRecord],
        guard: tuple[type[ProgressRecord], str, int] | None = None,
    ) -> None:
        try:
            self._commit(records, guard)
        except IntegrityError as error:
            raise AppError(
                "PROGRESS_CONFLICT",
                "Identificador de operação já utilizado ou referência conflitante.",
                409,
            ) from error

    def _commit(
        self,
        records: list[ProgressRecord],
        guard: tuple[type[ProgressRecord], str, int] | None,
    ) -> None:
        with Session(self.engine) as session, session.begin():
            if guard:
                cls, rid, expected = guard
                row_cls = MAPPING[cls]
                result = session.connection().execute(
                    update(row_cls)
                    .where(
                        row_cls.id == rid,
                        row_cls.version == expected,
                        row_cls.owner_id == LOCAL_PROFILE_ID,
                    )
                    .values(version=expected + 1)
                )
                if result.rowcount != 1:
                    raise AppError(
                        "FLASHCARD_CONFLICT",
                        "O cartão mudou. Recarregue antes de salvar.",
                        409,
                    )
            for record in records:
                record.updated_at = now()
                values = {k: getattr(record, k) for k in FIELDS[type(record)]}
                session.merge(
                    MAPPING[type(record)](
                        id=record.id,
                        owner_id=record.owner_id,
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                        version=record.version,
                        data_json=record.model_dump_json(),
                        **values,
                    )
                )
                session.flush()
