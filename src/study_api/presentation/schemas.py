from typing import Annotated, Literal, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

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


class MessageInput(Input):
    content: Prompt
    model_id: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    request_id: UUID


class MessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    status: str
    model_id: str
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
