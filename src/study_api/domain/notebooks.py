"""Documentos locais com tipos permitidos e limites de recursos explícitos."""

import base64
import json
import math
from typing import Literal, Protocol, TypeVar
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from study_api.domain.chat import LOCAL_PROFILE_ID, new_id, now


def safe_link(value: str) -> bool:
    return value.startswith("#/notebooks/") or urlsplit(value).scheme in {
        "https",
        "http",
        "mailto",
    }


def validate_document(value: dict[str, JsonValue]) -> dict[str, JsonValue]:
    allowed = {
        "doc": {"content"},
        "paragraph": {"content"},
        "text": {"text", "marks"},
        "heading": {"content", "attrs"},
        "bulletList": {"content"},
        "orderedList": {"content", "attrs"},
        "listItem": {"content"},
        "blockquote": {"content"},
        "codeBlock": {"content", "attrs"},
        "hardBreak": set(),
        "horizontalRule": set(),
        "table": {"content"},
        "tableRow": {"content"},
        "tableCell": {"content", "attrs"},
        "tableHeader": {"content", "attrs"},
        "formula": {"attrs"},
    }
    count = 0

    def visit(node: JsonValue, depth: int) -> None:
        nonlocal count
        count += 1
        if depth > 16 or count > 3000 or not isinstance(node, dict):
            raise ValueError("Documento excede os limites estruturais.")
        kind = node.get("type")
        if (
            not isinstance(kind, str)
            or kind not in allowed
            or set(node) - ({"type"} | allowed[kind])
        ):
            raise ValueError("Tipo ou propriedade de documento não permitido.")
        attrs = node.get("attrs", {})
        if not isinstance(attrs, dict):
            raise ValueError("Atributos inválidos.")  # noqa: TRY004 -- Pydantic converte ValueError em erro de validação.
        permitted = {
            "heading": {"level"},
            "orderedList": {"start", "type"},
            "codeBlock": {"language"},
            "tableCell": {"colspan", "rowspan", "colwidth"},
            "tableHeader": {"colspan", "rowspan", "colwidth"},
            "formula": {"latex"},
        }.get(kind, set())
        if set(attrs) - permitted:
            raise ValueError("Atributo não permitido.")
        if kind == "heading" and attrs.get("level") not in (1, 2, 3):
            raise ValueError("Nível de título inválido.")
        if kind == "formula" and (
            not isinstance(attrs.get("latex"), str) or len(str(attrs["latex"])) > 2000
        ):
            raise ValueError("Fórmula inválida.")
        if kind in {"tableCell", "tableHeader"}:
            for key in ("colspan", "rowspan"):
                if (
                    type(attrs.get(key, 1)) is not int
                    or not 1 <= int(str(attrs.get(key, 1))) <= 20
                ):
                    raise ValueError("Dimensão de tabela inválida.")
            widths = attrs.get("colwidth")
            if widths is not None and (
                not isinstance(widths, list)
                or len(widths) > 20
                or any(
                    type(w) is not int or not 1 <= int(str(w)) <= 2000 for w in widths
                )
            ):
                raise ValueError("Largura de tabela inválida.")
        if kind == "orderedList" and (
            type(attrs.get("start", 1)) is not int
            or not 1 <= int(str(attrs.get("start", 1))) <= 10000
            or attrs.get("type") not in (None, "1", "a", "A", "i", "I")
        ):
            raise ValueError("Lista inválida.")
        if kind == "codeBlock" and (
            attrs.get("language") is not None
            and (
                not isinstance(attrs["language"], str)
                or len(str(attrs["language"])) > 40
            )
        ):
            raise ValueError("Linguagem inválida.")
        if kind == "text" and (
            not isinstance(node.get("text"), str) or not node["text"]
        ):
            raise ValueError("Texto inválido.")
        marks = node.get("marks", [])
        if not isinstance(marks, list) or len(marks) > 8:
            raise ValueError("Marcas inválidas.")
        for mark in marks:
            if (
                not isinstance(mark, dict)
                or mark.get("type")
                not in {"bold", "italic", "strike", "code", "underline", "link"}
                or set(mark) - {"type", "attrs"}
            ):
                raise ValueError("Marca não permitida.")
            if mark["type"] == "link":
                a = mark.get("attrs")
                if (
                    not isinstance(a, dict)
                    or set(a) - {"href", "target", "rel", "class"}
                    or not isinstance(a.get("href"), str)
                    or not safe_link(str(a["href"]))
                    or a.get("target") not in (None, "_blank", "_self")
                    or a.get("class") is not None
                ):
                    raise ValueError("Link não permitido.")
            elif mark.get("attrs"):
                raise ValueError("Marca com atributos não permitidos.")
        children = node.get("content", [])
        if not isinstance(children, list):
            raise ValueError("Conteúdo inválido.")  # noqa: TRY004 -- Pydantic converte ValueError em erro de validação.
        for child in children:
            visit(child, depth + 1)
        inline = {"text", "hardBreak"}
        blocks = {
            "paragraph",
            "heading",
            "bulletList",
            "orderedList",
            "blockquote",
            "codeBlock",
            "horizontalRule",
            "table",
            "formula",
        }
        child_types = {
            "doc": blocks,
            "paragraph": inline,
            "heading": inline,
            "codeBlock": {"text"},
            "bulletList": {"listItem"},
            "orderedList": {"listItem"},
            "listItem": blocks - {"table"},
            "blockquote": blocks,
            "table": {"tableRow"},
            "tableRow": {"tableCell", "tableHeader"},
            "tableCell": blocks,
            "tableHeader": blocks,
        }.get(kind, set())
        if any(
            not isinstance(c, dict) or c.get("type") not in child_types
            for c in children
        ):
            raise ValueError("Estrutura de conteúdo incompatível com o editor.")
        if (
            kind
            in {
                "doc",
                "listItem",
                "tableCell",
                "tableHeader",
                "bulletList",
                "orderedList",
                "table",
                "tableRow",
                "blockquote",
            }
            and not children
        ):
            raise ValueError("Bloco precisa de conteúdo.")

    if value.get("type") != "doc" or len(json.dumps(value)) > 250000:
        raise ValueError("Documento inválido ou extenso demais.")
    visit(value, 0)
    return value


class NoteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default_factory=new_id)
    owner_id: str = LOCAL_PROFILE_ID
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
    version: int = 1


class Notebook(NoteRecord):
    title: str
    topic_id: str | None = None
    trail_id: str | None = None


class Folder(NoteRecord):
    notebook_id: str
    parent_id: str | None = None
    title: str


def empty_document() -> dict[str, JsonValue]:
    return {"type": "doc", "content": [{"type": "paragraph"}]}


class NotePage(NoteRecord):
    notebook_id: str
    folder_id: str | None = None
    title: str
    document: dict[str, JsonValue] = Field(default_factory=empty_document)
    tags: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    linked_page_ids: list[str] = Field(default_factory=list)

    _document = field_validator("document")(validate_document)


class PageRevision(NoteRecord):
    page_id: str
    snapshot: NotePage
    operation_id: str


class Clipping(NoteRecord):
    page_id: str
    message_id: str
    selected_text: str
    start: int
    end: int
    source: dict[str, JsonValue]
    operation_id: str


class DrawingScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["excalidraw"] = "excalidraw"
    version: Literal[2] = 2
    source: Literal["study-local"] = "study-local"
    elements: list[dict[str, JsonValue]] = Field(default_factory=list, max_length=2000)
    appState: dict[str, JsonValue] = Field(default_factory=dict)
    files: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("elements")
    @classmethod
    def elements_safe(
        cls, rows: list[dict[str, JsonValue]]
    ) -> list[dict[str, JsonValue]]:
        ids = set()
        for row in rows:
            if (
                row.get("type")
                not in {
                    "rectangle",
                    "diamond",
                    "ellipse",
                    "line",
                    "arrow",
                    "freedraw",
                    "text",
                    "image",
                    "frame",
                    "embeddable",
                }
                or not isinstance(row.get("id"), str)
                or row["id"] in ids
            ):
                raise ValueError("Elemento inválido ou duplicado.")
            ids.add(str(row["id"]))
            # Conteúdo embutido e links externos não entram em um quadro local.
            if row.get("type") == "embeddable" or row.get("link") is not None:
                raise ValueError(
                    "Links e conteúdo externo não são permitidos no quadro."
                )
            for k in ("x", "y", "width", "height", "angle"):
                v = row.get(k, 0)
                if (
                    not isinstance(v, (float, int))
                    or not math.isfinite(v)
                    or abs(v) > 1000000
                ):
                    raise ValueError("Coordenada inválida.")
            points = row.get("points", [])
            if (
                not isinstance(points, list)
                or len(points) > 20000
                or any(
                    not isinstance(p, list)
                    or len(p) != 2
                    or any(
                        not isinstance(n, (int, float))
                        or not math.isfinite(n)
                        or abs(n) > 1000000
                        for n in p
                    )
                    for p in points
                )
            ):
                raise ValueError("Traço inválido ou extenso demais.")
            if row.get("type") == "text" and (
                not isinstance(row.get("text"), str) or len(str(row["text"])) > 20000
            ):
                raise ValueError("Texto do quadro inválido.")
        return rows

    @field_validator("appState")
    @classmethod
    def state_safe(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if set(value) - {"viewBackgroundColor", "scrollX", "scrollY", "zoom"}:
            raise ValueError("Estado não persistível.")
        for key in ("scrollX", "scrollY"):
            number = value.get(key, 0)
            if (
                not isinstance(number, (int, float))
                or not math.isfinite(number)
                or abs(number) > 1000000
            ):
                raise ValueError("Posição de quadro inválida.")
        zoom = value.get("zoom", {"value": 1})
        if (
            not isinstance(zoom, dict)
            or set(zoom) != {"value"}
            or not isinstance(zoom["value"], (int, float))
            or not 0.1 <= zoom["value"] <= 30
        ):
            raise ValueError("Zoom inválido.")
        color = value.get("viewBackgroundColor", "#ffffff")
        if not isinstance(color, str) or len(color) > 32:
            raise ValueError("Cor de fundo inválida.")
        return value

    @field_validator("files")
    @classmethod
    def files_safe(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if len(value) > 10:
            raise ValueError("Limite de imagens excedido.")
        for file_id, file in value.items():
            if not isinstance(file, dict) or file.get("id") != file_id:
                raise ValueError("Arquivo inválido.")
            mime, data = file.get("mimeType"), file.get("dataURL")
            if (
                mime not in {"image/png", "image/jpeg", "image/webp"}
                or not isinstance(data, str)
                or not data.startswith(f"data:{mime};base64,")
            ):
                raise ValueError("Apenas imagens locais PNG, JPEG ou WebP.")
            try:
                raw = base64.b64decode(data.split(",", 1)[1], validate=True)
            except ValueError as e:
                raise ValueError("Imagem inválida.") from e
            valid = (
                (mime == "image/png" and raw.startswith(b"\x89PNG\r\n\x1a\n"))
                or (mime == "image/jpeg" and raw.startswith(b"\xff\xd8\xff"))
                or (
                    mime == "image/webp" and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
                )
            )
            if len(raw) > 512000 or not valid:
                raise ValueError("Imagem inválida ou maior que 500 KB.")
        return value


class Drawing(NoteRecord):
    page_id: str
    scene: DrawingScene = Field(default_factory=DrawingScene)
    operation_id: str = ""


N = TypeVar("N", bound=NoteRecord)


class NotebookRepository(Protocol):
    def get(self, cls: type[N], record_id: str) -> N: ...
    def all(
        self,
        cls: type[N],
        parent: tuple[str, str] | None = None,
        limit: int | None = None,
    ) -> list[N]: ...
    def commit(
        self,
        records: list[NoteRecord],
        guard: tuple[type[NoteRecord], str, int] | None = None,
    ) -> None: ...
