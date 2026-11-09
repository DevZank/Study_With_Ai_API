import json
from typing import cast

from pydantic import JsonValue

from study_api.application.chat import ChatService
from study_api.application.trail_service import TrailService
from study_api.domain.chat import AppError
from study_api.domain.content import PublicDocument
from study_api.domain.notebooks import (
    Clipping,
    Drawing,
    DrawingScene,
    Folder,
    Notebook,
    NotebookRepository,
    NotePage,
    PageRevision,
)
from study_api.domain.trails import ContentVersion, Module, Unit


class NotebookService:
    def __init__(
        self, repo: NotebookRepository, chat: ChatService, trails: TrailService
    ) -> None:
        self.repo, self.chat, self.trails = repo, chat, trails

    def notebook(self, nid: str, write: bool = False) -> Notebook:
        value = self.repo.get(Notebook, nid)
        if value.topic_id:
            topic = self.chat.topic(value.topic_id)
            if write and topic.status != "active":
                raise AppError(
                    "TOPIC_ARCHIVED",
                    "Restaure o tema antes de editar seu caderno.",
                    409,
                )
        return value

    def create_notebook(
        self, title: str, topic: str | None, trail: str | None
    ) -> Notebook:
        if trail:
            linked = self.trails.trail(trail, True)
            if topic and topic != linked.topic_id:
                raise AppError(
                    "INVALID_SCOPE", "Trilha não pertence ao tema informado.", 422
                )
            topic = linked.topic_id
        if topic and self.chat.topic(topic).status != "active":
            raise AppError(
                "TOPIC_ARCHIVED", "Restaure o tema antes de criar caderno.", 409
            )
        notebook = Notebook(title=title, topic_id=topic, trail_id=trail)
        self.repo.commit([notebook])
        return notebook

    def page(self, pid: str, write: bool = False) -> NotePage:
        page = self.repo.get(NotePage, pid)
        self.notebook(page.notebook_id, write)
        return page

    def folder(self, fid: str, nid: str, parent: str | None = None) -> Folder:
        folder = self.repo.get(Folder, fid)
        if folder.notebook_id != nid:
            raise AppError("INVALID_FOLDER", "Pasta pertence a outro caderno.", 422)
        visited = {parent} if parent else set()
        current: Folder | None = folder
        while current:
            if current.id in visited or len(visited) >= 8:
                raise AppError(
                    "FOLDER_CYCLE",
                    "Hierarquia inválida ou com mais de oito níveis.",
                    422,
                )
            visited.add(current.id)
            current = (
                self.repo.get(Folder, current.parent_id) if current.parent_id else None
            )
        return folder

    def create_folder(self, nid: str, title: str, parent: str | None) -> Folder:
        self.notebook(nid, True)
        value = Folder(notebook_id=nid, title=title, parent_id=parent)
        if parent:
            self.folder(parent, nid, value.id)
        self.repo.commit([value])
        return value

    def edit_folder(
        self, fid: str, title: str, parent: str | None, expected: int
    ) -> Folder:
        value = self.repo.get(Folder, fid)
        self.notebook(value.notebook_id, True)
        if parent:
            self.folder(parent, value.notebook_id, value.id)
        value.title, value.parent_id, value.version = title, parent, expected + 1
        self.repo.commit([value], (Folder, fid, expected))
        return value

    def create_page(self, nid: str, title: str, folder: str | None) -> NotePage:
        self.notebook(nid, True)
        if folder:
            self.folder(folder, nid)
        page = NotePage(notebook_id=nid, title=title, folder_id=folder)
        drawing = Drawing(id=page.id, page_id=page.id)
        self.repo.commit([page, drawing])
        return page

    def save_page(
        self, pid: str, expected: int, operation: str, values: dict[str, object]
    ) -> NotePage:
        page = self.page(pid, True)
        prior = next(
            iter(self.repo.all(PageRevision, ("operation_id", operation))),
            None,
        )
        if prior:
            if (
                prior.page_id != pid
                or prior.snapshot.version != expected + 1
                or any(getattr(prior.snapshot, k) != v for k, v in values.items())
            ):
                raise AppError(
                    "IDEMPOTENCY_CONFLICT", "Identificador usado com outra edição.", 409
                )
            return page
        candidate = NotePage.model_validate(
            {**page.model_dump(), **values, "version": expected + 1}
        )
        self.notebook(candidate.notebook_id, True)
        if candidate.folder_id:
            self.folder(candidate.folder_id, candidate.notebook_id)
        for tid in candidate.topic_ids:
            self.chat.topic(tid)
        for linked in candidate.linked_page_ids:
            if linked == pid:
                raise AppError("SELF_LINK", "Escolha outra página para vincular.", 422)
            self.page(linked)
        revision = PageRevision(page_id=pid, snapshot=candidate, operation_id=operation)
        self.repo.commit([candidate, revision], (NotePage, pid, expected))
        return candidate

    def source(self, mid: str) -> tuple[str, dict[str, JsonValue]]:
        message = self.chat.get_message(mid)
        conversation = self.chat.conversation(message.conversation_id)
        topic = self.chat.topic(conversation.topic_id)
        if message.role != "assistant" or message.status != "completed":
            raise AppError(
                "SOURCE_UNAVAILABLE", "Selecione uma resposta concluída da IA.", 422
            )
        text = message.content
        if message.document_json:
            doc = PublicDocument.model_validate_json(message.document_json)
            parts = [doc.title]
            for block in doc.blocks:
                b = block.model_dump()
                parts.extend(public_text(b))
                if block.type in {"quiz", "exercise"}:
                    parts.append(self.chat.repo.exercise(block.exercise_id).prompt)
            text = "\n\n".join(parts)
        source: dict[str, JsonValue] = {
            "topic_id": topic.id,
            "topic_title": topic.title,
            "conversation_id": conversation.id,
            "message_id": message.id,
            "message_created_at": message.created_at,
            "model_id": message.model_id,
            "trail_id": None,
            "module_id": None,
            "unit_id": None,
            "content_version_id": None,
        }
        version = next(
            (v for v in self.trails.repo.all(ContentVersion) if v.message_id == mid),
            None,
        )
        if version:
            unit = self.trails.repo.get(Unit, version.unit_id)
            module = self.trails.repo.get(Module, unit.module_id)
            source.update(
                trail_id=module.trail_id,
                module_id=module.id,
                unit_id=unit.id,
                content_version_id=version.id,
            )
        return text, source

    def clip(
        self,
        pid: str,
        mid: str,
        start: int,
        end: int,
        selected: str,
        expected: int,
        operation: str,
    ) -> NotePage:
        page = self.page(pid, True)
        prior = next(iter(self.repo.all(Clipping, ("operation_id", operation))), None)
        if prior:
            if (
                prior.page_id,
                prior.message_id,
                prior.start,
                prior.end,
                prior.selected_text,
            ) != (pid, mid, start, end, selected):
                raise AppError(
                    "IDEMPOTENCY_CONFLICT",
                    "Identificador usado para outro recorte.",
                    409,
                )
            return page
        text, source = self.source(mid)
        if start < 0 or end <= start or end > len(text) or text[start:end] != selected:
            raise AppError(
                "INVALID_SELECTION",
                "O intervalo não corresponde ao texto original.",
                422,
            )
        paragraph: dict[str, JsonValue] = {
            "type": "paragraph",
            "content": [{"type": "text", "text": selected}],
        }
        document = {
            **page.document,
            "content": [
                *cast(list[JsonValue], page.document.get("content", [])),
                paragraph,
            ],
        }
        updated = NotePage.model_validate(
            {**page.model_dump(), "document": document, "version": expected + 1}
        )
        clip = Clipping(
            page_id=pid,
            message_id=mid,
            selected_text=selected,
            start=start,
            end=end,
            source=source,
            operation_id=operation,
        )
        revision = PageRevision(page_id=pid, snapshot=updated, operation_id=operation)
        self.repo.commit([updated, clip, revision], (NotePage, pid, expected))
        return updated

    def drawing(self, pid: str) -> Drawing:
        self.page(pid)
        return self.repo.get(Drawing, pid)

    def save_drawing(
        self, pid: str, expected: int, operation: str, scene: DrawingScene
    ) -> Drawing:
        self.page(pid, True)
        value = self.drawing(pid)
        if len(scene.model_dump_json()) > 2500000:
            raise AppError("DRAWING_LIMIT", "Quadro excede o limite de 2,5 MB.", 422)
        if value.operation_id == operation:
            if value.scene != scene:
                raise AppError(
                    "IDEMPOTENCY_CONFLICT",
                    "Identificador usado para outro desenho.",
                    409,
                )
            return value
        value.scene, value.version, value.operation_id = scene, expected + 1, operation
        self.repo.commit([value], (Drawing, value.id, expected))
        return value


def searchable(page: NotePage) -> str:
    return (
        page.title
        + " "
        + " ".join(page.tags)
        + " "
        + json.dumps(page.document, ensure_ascii=False)
    ).casefold()


def public_text(value: JsonValue) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in public_text(item)]
    if isinstance(value, dict):
        return [
            text
            for key, item in value.items()
            if key not in {"type", "id", "exercise_id", "source", "target"}
            for text in public_text(item)
        ]
    return []
