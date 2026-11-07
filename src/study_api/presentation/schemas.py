from typing import Annotated, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, computed_field

from study_api.domain.content import Choice, Mode, PublicDocument

Title = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
Prompt = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TopicInput(Input):
    title: Title


class TopicPatch(Input):
    title: Title | None = None
    status: Literal["active", "archived", "deleted"] | None = None


class TopicView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    status: str
    created_at: str
    updated_at: str


class ConversationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    topic_id: str
    title: str
    created_at: str
    active_mode: Mode = "learn"


class ModeInput(Input):
    active_mode: Mode


class MessageInput(Input):
    content: Prompt
    model_id: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    request_id: UUID
    mode: Mode | None = None
    response_format: Literal["text", "blocks"] = "text"


class MessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    status: str
    model_id: str
    created_at: str
    mode: Mode = "learn"
    response_format: str = "text"
    notice: str = ""
    document_json: str = Field(default="", exclude=True)

    @computed_field
    def document(self) -> PublicDocument | None:
        return (
            PublicDocument.model_validate_json(self.document_json)
            if self.document_json
            else None
        )


class ExerciseView(BaseModel):
    id: str
    message_id: str
    kind: Literal["multiple_choice", "true_false", "fill_blank", "open"]
    prompt: str
    options: list[Choice]
    hints: list[str]
    hints_remaining: int
    solution: str | None
    explanation: str | None


class AttemptInput(Input):
    response: Prompt
    request_id: UUID


class AttemptView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    exercise_id: str
    response: str
    score: float | None
    feedback: str
    created_at: str


class JobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    message_id: str
    model_id: str
    status: str
    error_code: str
    error_message: str


T = TypeVar("T")


class Page[T](BaseModel):
    items: list[T]
    next_cursor: str | None = None


class ModelsView(BaseModel):
    models: list[str]
    provider: Literal["ollama"] = "ollama"
    local_only: bool = True


class StreamView(BaseModel):
    event_id: str
    job_id: str
    job: JobView
    message: MessageView


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict[str, str] = Field(default_factory=dict)


class ErrorView(BaseModel):
    error: ErrorDetail
