from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field, JsonValue, field_validator

from study_api.application.notebooks import NotebookService, searchable
from study_api.domain.notebooks import (
    Clipping,
    Drawing,
    DrawingScene,
    Folder,
    Notebook,
    NotePage,
    PageRevision,
    validate_document,
)
from study_api.presentation.schemas import Input, Title

router = APIRouter()


def service(request: Request) -> NotebookService:
    value: NotebookService = request.app.state.notebooks
    return value


S = Annotated[NotebookService, Depends(service)]


class NotebookInput(Input):
    title: Title
    topic_id: UUID | None = None
    trail_id: UUID | None = None


class FolderInput(Input):
    title: Title
    parent_id: UUID | None = None


class FolderPatch(FolderInput):
    expected_version: int = Field(ge=1)


class PageInput(Input):
    title: Title
    folder_id: UUID | None = None


class PagePatch(Input):
    expected_version: int = Field(ge=1)
    operation_id: UUID
    title: Title
    notebook_id: UUID
    folder_id: UUID | None = None
    document: dict[str, JsonValue]
    tags: list[Annotated[str, Field(min_length=1, max_length=40)]] = Field(
        default_factory=list, max_length=20
    )
    topic_ids: list[UUID] = Field(default_factory=list, max_length=20)
    linked_page_ids: list[UUID] = Field(default_factory=list, max_length=20)

    _document = field_validator("document")(validate_document)


class ClipInput(Input):
    message_id: UUID
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    selected_text: str = Field(min_length=1, max_length=10000)
    expected_version: int = Field(ge=1)
    operation_id: UUID


class DrawingInput(Input):
    expected_version: int = Field(ge=1)
    operation_id: UUID
    scene: DrawingScene


@router.get("/notebooks")
async def notebooks(s: S) -> list[Notebook]:
    rows = s.repo.all(Notebook)
    # Cadernos de temas na lixeira são preservados e ficam ocultos até restauração.
    return [
        n
        for n in rows
        if not n.topic_id or s.chat.get_topic(n.topic_id).status != "deleted"
    ]


@router.post("/notebooks", status_code=201)
async def create_notebook(body: NotebookInput, s: S) -> Notebook:
    return s.create_notebook(
        body.title,
        str(body.topic_id) if body.topic_id else None,
        str(body.trail_id) if body.trail_id else None,
    )


@router.get("/notebooks/{nid}/folders")
async def folders(nid: UUID, s: S) -> list[Folder]:
    s.notebook(str(nid))
    return s.repo.all(Folder, ("notebook_id", str(nid)))


@router.post("/notebooks/{nid}/folders", status_code=201)
async def create_folder(nid: UUID, body: FolderInput, s: S) -> Folder:
    return s.create_folder(
        str(nid), body.title, str(body.parent_id) if body.parent_id else None
    )


@router.patch("/folders/{fid}")
async def edit_folder(fid: UUID, body: FolderPatch, s: S) -> Folder:
    return s.edit_folder(
        str(fid),
        body.title,
        str(body.parent_id) if body.parent_id else None,
        body.expected_version,
    )


@router.get("/notebooks/{nid}/pages")
async def pages(
    nid: UUID, s: S, q: Annotated[str, Query(max_length=120)] = ""
) -> list[NotePage]:
    s.notebook(str(nid))
    return [
        p
        for p in s.repo.all(NotePage, ("notebook_id", str(nid)))
        if p.notebook_id == str(nid) and q.casefold() in searchable(p)
    ]


@router.post("/notebooks/{nid}/pages", status_code=201)
async def create_page(nid: UUID, body: PageInput, s: S) -> NotePage:
    return s.create_page(
        str(nid), body.title, str(body.folder_id) if body.folder_id else None
    )


@router.get("/pages/{pid}")
async def page(pid: UUID, s: S) -> NotePage:
    return s.page(str(pid))


@router.patch("/pages/{pid}")
async def save_page(pid: UUID, body: PagePatch, s: S) -> NotePage:
    values = body.model_dump(mode="json", exclude={"expected_version", "operation_id"})
    return s.save_page(str(pid), body.expected_version, str(body.operation_id), values)


@router.get("/pages/{pid}/revisions")
async def revisions(pid: UUID, s: S) -> list[PageRevision]:
    s.page(str(pid))
    return s.repo.all(PageRevision, ("page_id", str(pid)), 30)


@router.get("/pages/{pid}/clippings")
async def clippings(pid: UUID, s: S) -> list[Clipping]:
    s.page(str(pid))
    return s.repo.all(Clipping, ("page_id", str(pid)))


@router.post("/pages/{pid}/clippings", status_code=201)
async def clip(pid: UUID, body: ClipInput, s: S) -> NotePage:
    return s.clip(
        str(pid),
        str(body.message_id),
        body.start,
        body.end,
        body.selected_text,
        body.expected_version,
        str(body.operation_id),
    )


@router.get("/messages/{mid}/clipping-source")
async def source(mid: UUID, s: S) -> dict[str, object]:
    text, origin = s.source(str(mid))
    return {"text": text, "source": origin}


@router.get("/pages/{pid}/drawing")
async def drawing(pid: UUID, s: S) -> Drawing:
    return s.drawing(str(pid))


@router.put("/pages/{pid}/drawing")
async def save_drawing(pid: UUID, body: DrawingInput, s: S) -> Drawing:
    return s.save_drawing(
        str(pid), body.expected_version, str(body.operation_id), body.scene
    )
