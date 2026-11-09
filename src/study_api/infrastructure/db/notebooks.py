from sqlalchemy import Engine, ForeignKey, String, Text, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from study_api.domain.chat import LOCAL_PROFILE_ID, AppError, now
from study_api.domain.notebooks import (
    Clipping,
    Drawing,
    Folder,
    N,
    Notebook,
    NotePage,
    NoteRecord,
    PageRevision,
)
from study_api.infrastructure.db.models import Base, Record


class NoteData(Record, Base):
    __abstract__ = True
    version: Mapped[int]
    data_json: Mapped[str] = mapped_column(Text)


class NotebookRow(NoteData):
    __tablename__ = "notebooks"
    topic_id: Mapped[str | None] = mapped_column(ForeignKey("topics.id"))
    trail_id: Mapped[str | None] = mapped_column(ForeignKey("trails.id"))


class FolderRow(NoteData):
    __tablename__ = "notebook_folders"
    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("notebook_folders.id"))


class PageRow(NoteData):
    __tablename__ = "notebook_pages"
    notebook_id: Mapped[str] = mapped_column(ForeignKey("notebooks.id"), index=True)
    folder_id: Mapped[str | None] = mapped_column(ForeignKey("notebook_folders.id"))


class RevisionRow(NoteData):
    __tablename__ = "notebook_revisions"
    page_id: Mapped[str] = mapped_column(ForeignKey("notebook_pages.id"), index=True)
    operation_id: Mapped[str] = mapped_column(String(36), unique=True)


class ClippingRow(NoteData):
    __tablename__ = "saved_clippings"
    page_id: Mapped[str] = mapped_column(ForeignKey("notebook_pages.id"), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"))
    operation_id: Mapped[str] = mapped_column(String(36), unique=True)


class DrawingRow(NoteData):
    __tablename__ = "drawing_boards"
    page_id: Mapped[str] = mapped_column(ForeignKey("notebook_pages.id"), unique=True)


MAPPING: dict[type[NoteRecord], type[NoteData]] = {
    Notebook: NotebookRow,
    Folder: FolderRow,
    NotePage: PageRow,
    PageRevision: RevisionRow,
    Clipping: ClippingRow,
    Drawing: DrawingRow,
}
FIELDS: dict[type[NoteRecord], list[str]] = {
    Notebook: ["topic_id", "trail_id"],
    Folder: ["notebook_id", "parent_id"],
    NotePage: ["notebook_id", "folder_id"],
    PageRevision: ["page_id", "operation_id"],
    Clipping: ["page_id", "message_id", "operation_id"],
    Drawing: ["page_id"],
}


class SqliteNotebooks:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, cls: type[N], record_id: str) -> N:
        with Session(self.engine) as s:
            row = s.get(MAPPING[cls], record_id)
            if row is None or row.owner_id != LOCAL_PROFILE_ID:
                raise AppError("NOT_FOUND", "Registro do caderno não encontrado.", 404)
            return cls.model_validate_json(row.data_json)

    def all(
        self,
        cls: type[N],
        parent: tuple[str, str] | None = None,
        limit: int | None = None,
    ) -> list[N]:
        with Session(self.engine) as s:
            row = MAPPING[cls]
            query = select(row).where(row.owner_id == LOCAL_PROFILE_ID)
            if parent:
                if parent[0] not in FIELDS[cls]:
                    raise ValueError("Filtro não permitido no repositório.")
                query = query.where(getattr(row, parent[0]) == parent[1])
            query = (
                query.order_by(row.created_at.desc(), row.id.desc())
                if limit
                else query.order_by(row.created_at, row.id)
            )
            if limit:
                query = query.limit(limit)
            output = [cls.model_validate_json(r.data_json) for r in s.scalars(query)]
            return list(reversed(output)) if limit else output

    def commit(
        self,
        records: list[NoteRecord],
        guard: tuple[type[NoteRecord], str, int] | None = None,
    ) -> None:
        try:
            self._commit(records, guard)
        except IntegrityError as error:
            raise AppError(
                "NOTE_CONFLICT",
                "Identificador de operação já utilizado ou referência conflitante.",
                409,
            ) from error

    def _commit(
        self, records: list[NoteRecord], guard: tuple[type[NoteRecord], str, int] | None
    ) -> None:
        with Session(self.engine) as s, s.begin():
            if guard:
                cls, rid, expected = guard
                row = MAPPING[cls]
                result = s.connection().execute(
                    update(row)
                    .where(
                        row.id == rid,
                        row.version == expected,
                        row.owner_id == LOCAL_PROFILE_ID,
                    )
                    .values(version=expected + 1)
                )
                if result.rowcount != 1:
                    raise AppError(
                        "NOTE_CONFLICT",
                        "Outra edição foi salva. Seu rascunho foi preservado; recarregue antes de conciliar.",
                        409,
                    )
            for record in records:
                record.updated_at = now()
                values = {k: getattr(record, k) for k in FIELDS[type(record)]}
                s.merge(
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
                s.flush()
