from dataclasses import asdict
from typing import TypeVar, cast

from sqlalchemy import Engine, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from study_api.domain.chat import (
    LOCAL_PROFILE_ID,
    AppError,
    Conversation,
    Job,
    Message,
    Topic,
    now,
)
from study_api.domain.exercises import Exercise
from study_api.infrastructure.db.exercises import ExerciseStore
from study_api.infrastructure.db.models import (
    ConversationRow,
    ExerciseRow,
    JobRow,
    MessageRow,
    TopicRow,
)

T = TypeVar("T", Topic, Conversation, Message, Job)
ROWS: dict[
    type[Topic | Conversation | Message | Job],
    type[TopicRow | ConversationRow | MessageRow | JobRow],
] = {
    Topic: TopicRow,
    Conversation: ConversationRow,
    Message: MessageRow,
    Job: JobRow,
}


class SqliteRepository(ExerciseStore):
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def _get(self, cls: type[T], item_id: str) -> T:
        with Session(self.engine) as session:
            row = cast(
                TopicRow | ConversationRow | MessageRow | JobRow | None,
                session.get(ROWS[cls], item_id),
            )
            if row is None or row.owner_id != LOCAL_PROFILE_ID:
                raise AppError("NOT_FOUND", "Registro não encontrado.", 404)
            values = {name: getattr(row, name) for name in cls.__dataclass_fields__}
            return cls(**values)

    def _list(self, cls: type[T], parent: tuple[str, str] | None = None) -> list[T]:
        with Session(self.engine) as session:
            statement = select(ROWS[cls]).where(ROWS[cls].owner_id == LOCAL_PROFILE_ID)
            if parent:
                statement = statement.where(getattr(ROWS[cls], parent[0]) == parent[1])
            rows = session.scalars(
                statement.order_by(ROWS[cls].created_at, ROWS[cls].id)
            )
            return [
                cls(**{name: getattr(row, name) for name in cls.__dataclass_fields__})
                for row in rows
            ]

    def _save(self, item: T) -> T:
        item.updated_at = now()
        with Session(self.engine) as session, session.begin():
            session.merge(ROWS[type(item)](**asdict(item)))
        return item

    def topics(self) -> list[Topic]:
        return self._list(Topic)

    def topic(self, topic_id: str) -> Topic:
        return self._get(Topic, topic_id)

    def save_topic(self, topic: Topic) -> Topic:
        return self._save(topic)

    def conversations(self, topic_id: str) -> list[Conversation]:
        return self._list(Conversation, ("topic_id", topic_id))

    def conversation(self, conversation_id: str) -> Conversation:
        return self._get(Conversation, conversation_id)

    def save_conversation(self, conversation: Conversation) -> Conversation:
        return self._save(conversation)

    def messages(self, conversation_id: str) -> list[Message]:
        return self._list(Message, ("conversation_id", conversation_id))

    def message(self, message_id: str) -> Message:
        return self._get(Message, message_id)

    def save_message(self, message: Message) -> Message:
        return self._save(message)

    def job(self, job_id: str) -> Job:
        return self._get(Job, job_id)

    def jobs(self) -> list[Job]:
        return self._list(Job)

    def create_turn(self, user: Message, assistant: Message, job: Job) -> None:
        try:
            with Session(self.engine) as session, session.begin():
                session.add(MessageRow(**asdict(user)))
                session.add(MessageRow(**asdict(assistant)))
                session.flush()
                session.add(JobRow(**asdict(job)))
                timestamp = now()
                conversation = session.get(ConversationRow, job.conversation_id)
                if conversation is None:
                    raise AppError("NOT_FOUND", "Conversa não encontrada.", 404)
                conversation.updated_at = timestamp
                conversation.active_mode = assistant.mode
                session.execute(
                    update(TopicRow)
                    .where(TopicRow.id == conversation.topic_id)
                    .values(updated_at=timestamp)
                )
        except IntegrityError as error:
            raise AppError(
                "TURN_CONFLICT",
                "Já existe uma geração ou requisição com este identificador.",
                409,
            ) from error

    def save_job(self, job: Job, message: Message) -> None:
        self.save_result(job, message, [])

    def save_result(
        self, job: Job, message: Message, exercises: list[Exercise]
    ) -> None:
        job.updated_at = message.updated_at = now()
        with Session(self.engine) as session, session.begin():
            session.merge(JobRow(**asdict(job)))
            session.merge(MessageRow(**asdict(message)))
            session.flush()
            session.add_all(ExerciseRow(**asdict(exercise)) for exercise in exercises)
