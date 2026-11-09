from sqlalchemy import (
    Engine,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from study_api.domain.chat import LOCAL_PROFILE_ID, AppError, now
from study_api.domain.trails import (
    ContentVersion,
    LearningSummary,
    Module,
    R,
    Stored,
    Trail,
    TrailJob,
    Unit,
)
from study_api.infrastructure.db.models import Base, Record


class TrailData(Record, Base):
    __abstract__ = True
    data_json: Mapped[str] = mapped_column(Text)


class TrailRow(TrailData):
    __tablename__ = "trails"
    topic_id: Mapped[str] = mapped_column(ForeignKey("topics.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)


class ModuleRow(TrailData):
    __tablename__ = "trail_modules"
    trail_id: Mapped[str] = mapped_column(ForeignKey("trails.id"), index=True)


class UnitRow(TrailData):
    __tablename__ = "lessons"
    module_id: Mapped[str] = mapped_column(ForeignKey("trail_modules.id"), index=True)


class VersionRow(TrailData):
    __tablename__ = "lesson_versions"
    unit_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))


class SummaryRow(TrailData):
    __tablename__ = "learning_summaries"
    version_id: Mapped[str] = mapped_column(
        ForeignKey("lesson_versions.id"), index=True
    )


class TrailJobRow(TrailData):
    __tablename__ = "trail_jobs"
    target_id: Mapped[str] = mapped_column(String(36))
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    status: Mapped[str]
    __table_args__ = (
        Index(
            "one_active_trail_target",
            "target_id",
            unique=True,
            sqlite_where=text("status = 'running'"),
        ),
    )


MAPPING: dict[type[Stored], type[TrailData]] = {
    Trail: TrailRow,
    Module: ModuleRow,
    Unit: UnitRow,
    ContentVersion: VersionRow,
    LearningSummary: SummaryRow,
    TrailJob: TrailJobRow,
}
PARENTS: dict[type[Stored], list[str]] = {
    Trail: ["topic_id", "version"],
    Module: ["trail_id"],
    Unit: ["module_id"],
    ContentVersion: ["unit_id", "message_id"],
    LearningSummary: ["version_id"],
    TrailJob: ["target_id", "request_id", "status"],
}


class SqliteTrails:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, cls: type[R], record_id: str) -> R:
        with Session(self.engine) as session:
            row = session.get(MAPPING[cls], record_id)
            if row is None or row.owner_id != LOCAL_PROFILE_ID:
                raise AppError("NOT_FOUND", "Registro da trilha não encontrado.", 404)
            return cls.model_validate_json(row.data_json)

    def all(self, cls: type[R], parent: tuple[str, str] | None = None) -> list[R]:
        with Session(self.engine) as session:
            statement = select(MAPPING[cls]).where(
                MAPPING[cls].owner_id == LOCAL_PROFILE_ID
            )
            if parent:
                statement = statement.where(
                    getattr(MAPPING[cls], parent[0]) == parent[1]
                )
            rows = session.scalars(
                statement.order_by(MAPPING[cls].created_at, MAPPING[cls].id)
            )
            return [cls.model_validate_json(row.data_json) for row in rows]

    def commit(
        self, records: list[Stored], guard: tuple[str, int] | None = None
    ) -> None:
        try:
            with Session(self.engine) as session, session.begin():
                if guard:
                    result = session.connection().execute(
                        update(TrailRow)
                        .where(
                            TrailRow.id == guard[0],
                            TrailRow.version == guard[1],
                            TrailRow.owner_id == LOCAL_PROFILE_ID,
                        )
                        .values(version=guard[1] + 1)
                    )
                    if result.rowcount != 1:
                        raise AppError(
                            "STALE_PLAN",
                            "O plano mudou. Atualize antes de salvar.",
                            409,
                        )
                for record in records:
                    record.updated_at = now()
                    values = {
                        key: getattr(record, key) for key in PARENTS[type(record)]
                    }
                    session.merge(
                        MAPPING[type(record)](
                            id=record.id,
                            owner_id=record.owner_id,
                            created_at=record.created_at,
                            updated_at=record.updated_at,
                            data_json=record.model_dump_json(),
                            **values,
                        )
                    )
                    session.flush()
        except IntegrityError as error:
            raise AppError(
                "TRAIL_CONFLICT",
                "Já existe uma operação com esse identificador ou unidade.",
                409,
            ) from error
