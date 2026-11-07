import unicodedata
from dataclasses import dataclass, field
from typing import Literal

from study_api.domain.chat import LOCAL_PROFILE_ID, new_id, now

Kind = Literal["multiple_choice", "true_false", "fill_blank", "open"]


@dataclass
class Exercise:
    message_id: str
    kind: Kind
    prompt: str
    options_json: str
    answer_key: str
    explanation: str
    hints_json: str
    id: str = field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    hints_revealed: int = 0
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


@dataclass
class Attempt:
    exercise_id: str
    response: str
    request_id: str
    score: float | None
    feedback: str
    id: str = field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


def normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def grade(exercise: Exercise, response: str, request_id: str) -> Attempt:
    score = (
        None
        if exercise.kind == "open"
        else float(normalize(response) == normalize(exercise.answer_key))
    )
    if score is None:
        feedback = "Resposta registrada para revisão. Compare com a referência; nenhuma nota automática foi atribuída."
    else:
        feedback = (
            "Resposta de acordo com o gabarito. "
            if score == 1
            else "Resposta diferente do gabarito. "
        ) + exercise.explanation
    return Attempt(exercise.id, response, request_id, score, feedback)
