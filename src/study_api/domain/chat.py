from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal, Protocol
from uuid import uuid4

Status = Literal["running", "completed", "failed", "cancelled", "interrupted"]
LOCAL_PROFILE_ID = "00000000-0000-0000-0000-000000000001"


def new_id() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(UTC).isoformat()


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass
class Topic:
    title: str
    id: str = field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    status: str = "active"
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


@dataclass
class Conversation:
    topic_id: str
    title: str = "Nova conversa"
    id: str = field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


@dataclass
class Message:
    conversation_id: str
    role: str
    content: str
    status: str = "completed"
    model_id: str = ""
    id: str = field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


@dataclass
class Job:
    conversation_id: str
    message_id: str
    model_id: str
    request_id: str
    request_hash: str
    id: str = field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    status: str = "running"
    error_code: str = ""
    error_message: str = ""
    created_at: str = field(default_factory=now)
    updated_at: str = field(default_factory=now)


class Repository(Protocol):
    def topics(self) -> list[Topic]: ...
    def topic(self, topic_id: str) -> Topic: ...
    def save_topic(self, topic: Topic) -> Topic: ...
    def conversations(self, topic_id: str) -> list[Conversation]: ...
    def conversation(self, conversation_id: str) -> Conversation: ...
    def save_conversation(self, conversation: Conversation) -> Conversation: ...
    def messages(self, conversation_id: str) -> list[Message]: ...
    def message(self, message_id: str) -> Message: ...
    def save_message(self, message: Message) -> Message: ...
    def job(self, job_id: str) -> Job: ...
    def jobs(self) -> list[Job]: ...
    def create_turn(self, user: Message, assistant: Message, job: Job) -> None: ...
    def save_job(self, job: Job, message: Message) -> None: ...


class Provider(Protocol):
    async def models(self) -> list[str]: ...
    async def validate_model(self, model: str) -> None: ...
    def chat(
        self, model: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]: ...
