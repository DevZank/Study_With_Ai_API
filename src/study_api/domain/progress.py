"""Domínio de memorização espaçada (FSRS), métricas pedagógicas e gamificação leve."""

import math
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from study_api.domain.chat import LOCAL_PROFILE_ID, AppError, new_id, now
from study_api.domain.content import Short, Text

Rating = Literal[1, 2, 3, 4]
CardState = Literal["new", "learning", "review", "relearning"]

# Pesos padrão FSRS-4.5 para agendamento determinístico local sem dependência externa.
FSRS_WEIGHTS: tuple[float, ...] = (
    0.4,
    1.2,
    3.2,
    8.0,
    4.93,
    0.94,
    0.86,
    0.01,
    1.49,
    0.14,
    0.94,
    2.18,
    0.05,
    0.34,
    1.26,
    0.29,
    2.61,
)
DESIRED_RETENTION = 0.9
DECAY = -0.5
FACTOR = 19.0 / 81.0
DAILY_REVIEW_XP_CAP = 30
XP_PER_LEVEL = 100


def parse_utc(value: str) -> datetime:
    """Converte timestamp ISO-8601 para datetime UTC explícito."""
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise AppError(
            "INVALID_TIMESTAMP", "Data/hora inválida; utilize formato ISO-8601.", 422
        ) from error
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def format_utc(value: datetime) -> str:
    """Serializa datetime em UTC no formato ISO-8601 ordenável lexicograficamente."""
    return value.astimezone(UTC).isoformat()


def concept_slug(name: str) -> str:
    """Normaliza o nome de um conceito para deduplicação determinística por tema."""
    normalized = unicodedata.normalize("NFKC", name).casefold().strip()
    cleaned = re.sub(r"[^\w\s-]", "", normalized)
    collapsed = re.sub(r"[\s_-]+", "-", cleaned).strip("-")
    return (collapsed or "conceito")[:80]


class ProgressRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
    version: int = 1


class Flashcard(ProgressRecord):
    topic_id: str
    concept_id: str | None = None
    concept_name: Short = "Conceito geral"
    front: Text
    back: Text
    source_type: Literal["manual", "message_block", "notebook_page"] = "manual"
    source_ref: dict[str, JsonValue] = Field(default_factory=dict)
    source_key: str | None = None
    operation_id: str = ""
    archived: bool = False


class ReviewState(ProgressRecord):
    flashcard_id: str
    topic_id: str
    due_at: str = Field(default_factory=now)
    stability: float = 0.0
    difficulty: float = 0.0
    reps: int = 0
    lapses: int = 0
    state: CardState = "new"
    last_reviewed_at: str | None = None


class ReviewEvent(ProgressRecord):
    review_state_id: str
    flashcard_id: str
    request_id: str
    rating: Rating
    reviewed_at: str
    elapsed_days: float
    scheduled_days: float
    stability_before: float
    stability_after: float
    difficulty_before: float
    difficulty_after: float
    was_due: bool
    xp_awarded: int = 0


class Concept(ProgressRecord):
    topic_id: str
    slug: str
    name: Short
    definition: str = ""
    source_type: Literal["trail", "exercise", "flashcard", "manual"] = "manual"


class ConceptMastery(ProgressRecord):
    concept_id: str
    topic_id: str
    concept_name: str
    score: float | None = None
    evidence_count: int = 0
    objective_attempts: int = 0
    correct_attempts: int = 0
    review_count: int = 0
    uncertainty: Literal["unestimated", "high", "moderate", "low"] = "unestimated"
    last_assessed_at: str | None = None


class XpEvent(ProgressRecord):
    topic_id: str | None = None
    source_type: Literal[
        "exercise_first_try",
        "exercise_correct",
        "flashcard_review",
        "unit_completion",
    ]
    source_id: str
    source_key: str
    points: int
    reason: str


class AchievementDefinition(ProgressRecord):
    code: str
    title: str
    description: str
    rule: dict[str, JsonValue]


class EarnedAchievement(ProgressRecord):
    achievement_id: str
    code: str
    title: str
    description: str
    earned_at: str = Field(default_factory=now)


class ProgressPreference(ProgressRecord):
    hide_gamification: bool = False


DEFAULT_ACHIEVEMENTS: tuple[tuple[str, str, str, dict[str, JsonValue]], ...] = (
    (
        "first_practice",
        "Primeira Prática",
        "Registrou a primeira tentativa em um exercício.",
        {"metric": "exercise_attempts", "min": 1},
    ),
    (
        "accurate_practice",
        "Resolução Verificada",
        "Respondeu a um exercício objetivo de acordo com o gabarito.",
        {"metric": "correct_exercises", "min": 1},
    ),
    (
        "first_review",
        "Memória Ativa",
        "Concluiu a primeira revisão espaçada FSRS de um flashcard.",
        {"metric": "review_events", "min": 1},
    ),
    (
        "trail_step",
        "Passo na Trilha",
        "Concluiu uma unidade de trilha com resumo estruturado.",
        {"metric": "completed_units", "min": 1},
    ),
    (
        "consistent_learner",
        "Ciclo Completo",
        "Praticou exercícios e revisou flashcards em seus estudos.",
        {"metric": "combined_practice_and_review", "min": 1},
    ),
)


def retrievability_at(state: ReviewState, at_time: str) -> float | None:
    """Calcula a probabilidade estimada de recordação R(t, S) pela curva FSRS."""
    if state.reps <= 0 or state.stability <= 0 or not state.last_reviewed_at:
        return None
    reviewed = parse_utc(state.last_reviewed_at)
    current = parse_utc(at_time)
    elapsed_days = max(0.0, (current - reviewed).total_seconds() / 86400.0)
    retention = math.pow(1.0 + FACTOR * (elapsed_days / state.stability), DECAY)
    return round(min(1.0, max(0.0, retention)), 4)


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


def _initial_difficulty(rating: Rating) -> float:
    w4, w5 = FSRS_WEIGHTS[4], FSRS_WEIGHTS[5]
    return round(_clamp(w4 - math.exp(w5 * (rating - 1)) + 1.0, 1.0, 10.0), 4)


def _next_difficulty(difficulty: float, rating: Rating) -> float:
    w6, w7 = FSRS_WEIGHTS[6], FSRS_WEIGHTS[7]
    delta = -w6 * (rating - 3)
    damped = difficulty + delta * ((10.0 - difficulty) / 9.0)
    target = _initial_difficulty(4)
    return round(_clamp(w7 * target + (1.0 - w7) * damped, 1.0, 10.0), 4)


def _next_recall_stability(
    stability: float, difficulty: float, retention: float, rating: Rating
) -> float:
    w8, w9, w10, w15, w16 = (
        FSRS_WEIGHTS[8],
        FSRS_WEIGHTS[9],
        FSRS_WEIGHTS[10],
        FSRS_WEIGHTS[15],
        FSRS_WEIGHTS[16],
    )
    hard_penalty = w15 if rating == 2 else 1.0
    easy_bonus = w16 if rating == 4 else 1.0
    growth = (
        math.exp(w8)
        * (11.0 - difficulty)
        * math.pow(max(stability, 0.1), -w9)
        * (math.exp(w10 * (1.0 - retention)) - 1.0)
        * hard_penalty
        * easy_bonus
    )
    return round(_clamp(stability * (1.0 + growth), 0.2, 3650.0), 4)


def _next_forget_stability(
    stability: float, difficulty: float, retention: float
) -> float:
    w11, w12, w13, w14 = (
        FSRS_WEIGHTS[11],
        FSRS_WEIGHTS[12],
        FSRS_WEIGHTS[13],
        FSRS_WEIGHTS[14],
    )
    post_lapse = (
        w11
        * math.pow(max(difficulty, 1.0), -w12)
        * (math.pow(stability + 1.0, w13) - 1.0)
        * math.exp(w14 * (1.0 - retention))
    )
    return round(_clamp(min(stability, post_lapse), 0.2, 3650.0), 4)


def _interval_days(stability: float, rating: Rating) -> float:
    """Converte estabilidade FSRS no intervalo determinístico em dias até o próximo vencimento."""
    if rating == 1:
        # Lapsos voltam em 6 horas (0,25 dia) para reforço no mesmo ciclo sem travar a fila imediata.
        return 0.25
    # Para R_d = 0.9, (R_d^(1/DECAY) - 1) / FACTOR == 1.0, logo o intervalo base equivale a S.
    factor = (math.pow(DESIRED_RETENTION, 1.0 / DECAY) - 1.0) / FACTOR
    raw = stability * factor
    minimum = 1.0 if rating == 2 else (2.0 if rating == 3 else 4.0)
    return round(max(minimum, min(3650.0, raw)), 2)


def schedule_review(
    state: ReviewState,
    rating: Rating,
    reviewed_at: str,
    request_id: str,
) -> tuple[ReviewState, ReviewEvent]:
    """Aplica uma revisão FSRS determinística e produz o novo estado e o evento imutável."""
    current_dt = parse_utc(reviewed_at)
    due_dt = parse_utc(state.due_at)
    was_due = current_dt >= due_dt
    stability_before = state.stability
    difficulty_before = state.difficulty

    if state.reps == 0 or state.last_reviewed_at is None:
        elapsed_days = 0.0
        new_difficulty = _initial_difficulty(rating)
        new_stability = round(FSRS_WEIGHTS[rating - 1], 4)
        new_lapses = 1 if rating == 1 else 0
        new_state: CardState = "learning" if rating == 1 else "review"
    else:
        last_dt = parse_utc(state.last_reviewed_at)
        elapsed_days = round(
            max(0.0, (current_dt - last_dt).total_seconds() / 86400.0), 4
        )
        retention = retrievability_at(state, reviewed_at) or DESIRED_RETENTION
        new_difficulty = _next_difficulty(state.difficulty, rating)
        if rating == 1:
            new_stability = _next_forget_stability(
                state.stability, new_difficulty, retention
            )
            new_lapses = state.lapses + 1
            new_state = "relearning"
        else:
            new_stability = _next_recall_stability(
                state.stability, new_difficulty, retention, rating
            )
            new_lapses = state.lapses
            new_state = "review"

    scheduled_days = _interval_days(new_stability, rating)
    next_due = format_utc(current_dt + timedelta(days=scheduled_days))

    updated_state = state.model_copy(
        update={
            "due_at": next_due,
            "stability": new_stability,
            "difficulty": new_difficulty,
            "reps": state.reps + 1,
            "lapses": new_lapses,
            "state": new_state,
            "last_reviewed_at": format_utc(current_dt),
            "version": state.version + 1,
        }
    )
    event = ReviewEvent(
        review_state_id=state.id,
        flashcard_id=state.flashcard_id,
        request_id=request_id,
        rating=rating,
        reviewed_at=format_utc(current_dt),
        elapsed_days=elapsed_days,
        scheduled_days=scheduled_days,
        stability_before=stability_before,
        stability_after=new_stability,
        difficulty_before=difficulty_before,
        difficulty_after=new_difficulty,
        was_due=was_due,
    )
    return updated_state, event


def calculate_concept_mastery(
    concept: Concept,
    objective_scores: list[tuple[float, str]],
    review_ratings: list[tuple[Rating, str]],
) -> ConceptMastery:
    """
    Calcula o domínio estimado de um conceito a partir de tentativas objetivas e revisões.

    Esta métrica não se confunde com conclusão de trilha nem com retenção temporal FSRS:
    ela reflete apenas a proporção ponderada de acertos/desempenho nas evidências observadas.
    """
    weights: list[tuple[str, float, float]] = []
    for score, timestamp in objective_scores:
        # Tentativas objetivas têm peso 1.0 na evidência de domínio.
        weights.append((timestamp, float(score), 1.0))
    rating_map: dict[Rating, float] = {1: 0.0, 2: 0.55, 3: 0.85, 4: 1.0}
    for rating, timestamp in review_ratings:
        # Revisões têm peso complementar (0.6) para não substituir exercícios práticos.
        weights.append((timestamp, rating_map[rating], 0.6))

    evidence_count = len(objective_scores) + len(review_ratings)
    if not weights:
        return ConceptMastery(
            concept_id=concept.id,
            topic_id=concept.topic_id,
            concept_name=concept.name,
            score=None,
            evidence_count=0,
            objective_attempts=0,
            correct_attempts=0,
            review_count=0,
            uncertainty="unestimated",
            last_assessed_at=None,
        )

    weights.sort(key=lambda item: item[0])
    total_weight = sum(w for _, _, w in weights)
    weighted_sum = sum(val * w for _, val, w in weights)
    raw_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    uncertainty: Literal["unestimated", "high", "moderate", "low"]
    if evidence_count < 2:
        uncertainty = "high"
    elif evidence_count < 5:
        uncertainty = "moderate"
    else:
        uncertainty = "low"

    return ConceptMastery(
        concept_id=concept.id,
        topic_id=concept.topic_id,
        concept_name=concept.name,
        score=round(_clamp(raw_score, 0.0, 1.0), 4),
        evidence_count=evidence_count,
        objective_attempts=len(objective_scores),
        correct_attempts=sum(1 for s, _ in objective_scores if s >= 1.0),
        review_count=len(review_ratings),
        uncertainty=uncertainty,
        last_assessed_at=weights[-1][0],
    )


def level_progress(total_xp: int) -> dict[str, int]:
    """Calcula nível atual e progresso para o próximo nível de forma determinística."""
    safe_xp = max(0, total_xp)
    return {
        "total_xp": safe_xp,
        "level": 1 + (safe_xp // XP_PER_LEVEL),
        "current_level_xp": safe_xp % XP_PER_LEVEL,
        "next_level_xp": XP_PER_LEVEL,
    }


P = TypeVar("P", bound=ProgressRecord)


class ProgressRepository(Protocol):
    def get(self, cls: type[P], record_id: str) -> P: ...
    def find_by(self, cls: type[P], field: str, value: str) -> P | None: ...
    def all(
        self,
        cls: type[P],
        parent: tuple[str, str] | None = None,
    ) -> list[P]: ...
    def commit(
        self,
        records: list[ProgressRecord],
        guard: tuple[type[ProgressRecord], str, int] | None = None,
    ) -> None: ...
