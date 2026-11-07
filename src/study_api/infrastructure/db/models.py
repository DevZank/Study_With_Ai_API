from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
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


class MessageRow(Record, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str]
    content: Mapped[str] = mapped_column(Text)
    model_id: Mapped[str]
    status: Mapped[str]
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
    model_id: Mapped[str]
    request_id: Mapped[str] = mapped_column(unique=True)
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
