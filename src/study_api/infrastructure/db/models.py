from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True)
    created_at: Mapped[str]
    updated_at: Mapped[str]


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(primary_key=True)
    display_name: Mapped[str]


class TopicRow(Record, Base):
    __tablename__ = "topics"
    title: Mapped[str] = mapped_column(String(120))
    status: Mapped[str]
    __table_args__ = (CheckConstraint("status IN ('active','archived','deleted')"),)


class ConversationRow(Record, Base):
    __tablename__ = "conversations"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    title: Mapped[str]
    active_mode: Mapped[str] = mapped_column(server_default="learn")
    origin: Mapped[str] = mapped_column(server_default="free")


class MessageRow(Record, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str]
    status: Mapped[str]
    mode: Mapped[str] = mapped_column(server_default="learn")
    response_format: Mapped[str] = mapped_column(server_default="text")
    document_json: Mapped[str] = mapped_column(Text, server_default="")
    notice: Mapped[str] = mapped_column(Text, server_default="")
    __table_args__ = (
        CheckConstraint("role IN ('user','assistant')"),
        CheckConstraint(
            "status IN ('running','completed','failed','cancelled','interrupted')"
        ),
    )


class JobRow(Record, Base):
    __tablename__ = "generation_jobs"
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))
    request_id: Mapped[str] = mapped_column(unique=True)
    model_id: Mapped[str]
    request_hash: Mapped[str]
    status: Mapped[str]
    error_code: Mapped[str]
    error_message: Mapped[str]
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','completed','failed','cancelled','interrupted')"
        ),
        Index(
            "one_running_job",
            "conversation_id",
            unique=True,
            sqlite_where=text("status = 'running'"),
        ),
    )


class ExerciseRow(Record, Base):
    __tablename__ = "exercises"
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), index=True)
    kind: Mapped[str]
    prompt: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text)
    answer_key: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    hints_json: Mapped[str] = mapped_column(Text)
    hints_revealed: Mapped[int] = mapped_column(server_default="0")
    __table_args__ = (
        CheckConstraint("kind IN ('multiple_choice','true_false','fill_blank','open')"),
    )


class AttemptRow(Record, Base):
    __tablename__ = "exercise_attempts"
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"), index=True)
    response: Mapped[str] = mapped_column(Text)
    request_id: Mapped[str] = mapped_column(unique=True)
    score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str] = mapped_column(Text)
