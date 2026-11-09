"""Integração de cadernos com banco temporário; nenhum dado é enviado à IA."""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from test_chat import TestProvider
from test_trails import TrailProvider, planned, wait

from study_api.domain.chat import Conversation, Message, Topic
from study_api.domain.notebooks import DrawingScene, NotePage
from study_api.main import create_app


def test_pages_folders_clippings_conflicts_and_restart(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database, TestProvider())
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c,
        ):

            async def post(path: str, body: dict[str, object]) -> dict[str, object]:
                r = await c.post("/api/v1" + path, json=body)
                assert r.status_code == 201, r.text
                result: dict[str, object] = r.json()
                return result

            topic = app.state.service.repo.save_topic(Topic("Tema original"))
            conv = app.state.service.repo.save_conversation(Conversation(topic.id))
            message = app.state.service.repo.save_message(
                Message(conv.id, "assistant", "Resposta 😀 original de teste.")
            )
            global_book = await post("/notebooks", {"title": "Global"})
            theme_book = await post(
                "/notebooks", {"title": "Tema", "topic_id": topic.id}
            )
            folder = await post(
                f"/notebooks/{theme_book['id']}/folders", {"title": "Pasta"}
            )
            child = await post(
                f"/notebooks/{theme_book['id']}/folders",
                {"title": "Filha", "parent_id": folder["id"]},
            )
            cycle = await c.patch(
                f"/api/v1/folders/{folder['id']}",
                json={
                    "title": "Pasta",
                    "parent_id": child["id"],
                    "expected_version": 1,
                },
            )
            assert cycle.status_code == 422
            page = await post(
                f"/notebooks/{global_book['id']}/pages", {"title": "Minha nota"}
            )
            pid = str(page["id"])
            values = {
                k: page[k]
                for k in (
                    "title",
                    "notebook_id",
                    "folder_id",
                    "document",
                    "tags",
                    "topic_ids",
                    "linked_page_ids",
                )
            }
            values.update(
                notebook_id=theme_book["id"],
                folder_id=child["id"],
                tags=["soma"],
                topic_ids=[topic.id],
                document={
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Texto autoral",
                                    "marks": [{"type": "bold"}],
                                }
                            ],
                        }
                    ],
                },
            )
            body = {**values, "expected_version": 1, "operation_id": str(uuid4())}
            saved = await c.patch(f"/api/v1/pages/{pid}", json=body)
            assert saved.status_code == 200, saved.text
            assert (await c.patch(f"/api/v1/pages/{pid}", json=body)).status_code == 200
            assert (
                await c.patch(
                    f"/api/v1/pages/{pid}", json={**body, "operation_id": str(uuid4())}
                )
            ).status_code == 409
            found = (
                await c.get(f"/api/v1/notebooks/{theme_book['id']}/pages?q=autoral")
            ).json()
            assert len(found) == 1 and found[0]["folder_id"] == child["id"]
            clip_body = {
                "message_id": message.id,
                "start": 0,
                "end": len(message.content),
                "selected_text": message.content,
                "expected_version": 2,
                "operation_id": str(uuid4()),
            }
            clip = await c.post(f"/api/v1/pages/{pid}/clippings", json=clip_body)
            assert clip.status_code == 201, clip.text
            assert (
                await c.post(f"/api/v1/pages/{pid}/clippings", json=clip_body)
            ).status_code == 201
            assert (
                await c.post(
                    f"/api/v1/pages/{pid}/clippings",
                    json={
                        **clip_body,
                        "selected_text": "forjado",
                        "operation_id": str(uuid4()),
                    },
                )
            ).status_code == 422
            clips = (await c.get(f"/api/v1/pages/{pid}/clippings")).json()
            assert len(clips) == 1 and clips[0]["source"]["topic_id"] == topic.id
            assert clips[0]["source"]["message_created_at"] == message.created_at
            current = clip.json()
            edited = {
                **{k: current[k] for k in values},
                "document": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Cópia editada"}],
                        }
                    ],
                },
                "expected_version": 3,
                "operation_id": str(uuid4()),
            }
            assert (
                await c.patch(f"/api/v1/pages/{pid}", json=edited)
            ).status_code == 200
            assert app.state.service.get_message(message.id).content == message.content
            assert (await c.get(f"/api/v1/pages/{pid}/clippings")).json()[0][
                "selected_text"
            ] == message.content
            drawing = {
                "scene": {
                    "type": "excalidraw",
                    "version": 2,
                    "source": "study-local",
                    "elements": [
                        {
                            "id": "rectangle",
                            "type": "rectangle",
                            "x": 10,
                            "y": 20,
                            "width": 100,
                            "height": 50,
                        }
                    ],
                    "appState": {"scrollX": 0, "scrollY": 0, "zoom": {"value": 1}},
                    "files": {},
                },
                "expected_version": 1,
                "operation_id": str(uuid4()),
            }
            result = await c.put(f"/api/v1/pages/{pid}/drawing", json=drawing)
            assert result.status_code == 200, result.text
            assert (
                await c.put(f"/api/v1/pages/{pid}/drawing", json=drawing)
            ).status_code == 200
            assert (
                await c.put(
                    f"/api/v1/pages/{pid}/drawing",
                    json={**drawing, "operation_id": str(uuid4())},
                )
            ).status_code == 409
        app = create_app(database, TestProvider())
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c,
        ):
            assert (await c.get(f"/api/v1/pages/{pid}")).json()["version"] == 4
            assert len((await c.get(f"/api/v1/pages/{pid}/revisions")).json()) == 3
            assert (await c.get(f"/api/v1/pages/{pid}/drawing")).json()["scene"][
                "elements"
            ][0]["id"] == "rectangle"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "node",
    [
        {"type": "html", "text": "<script>alert(1)</script>"},
        {"type": "paragraph", "attrs": {"onclick": "alert(1)"}},
        {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": "X",
                    "marks": [
                        {"type": "link", "attrs": {"href": "javascript:alert(1)"}}
                    ],
                }
            ],
        },
        {"type": "image", "attrs": {"src": "https://external.invalid/pixel"}},
        {"type": "table", "content": [{"type": "text", "text": "inválido"}]},
    ],
)
def test_rejects_untrusted_document(node: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        NotePage.model_validate(
            {
                "notebook_id": str(uuid4()),
                "title": "Nota",
                "document": {"type": "doc", "content": [node]},
            }
        )


@pytest.mark.parametrize(
    "scene",
    [
        {
            "elements": [
                {"id": "x", "type": "embeddable", "link": "https://external.invalid"}
            ]
        },
        {"elements": [{"id": "x", "type": "rectangle", "link": "javascript:alert(1)"}]},
        {
            "files": {
                "x": {
                    "id": "x",
                    "mimeType": "image/svg+xml",
                    "dataURL": "data:image/svg+xml;base64,PHN2Zz4=",
                }
            }
        },
        {"appState": {"collaborators": {}}},
    ],
)
def test_rejects_untrusted_drawing(scene: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DrawingScene.model_validate(scene)


def test_trail_source_global_and_topic_notebooks(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database, TrailProvider())
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c,
        ):
            tid = await planned(c)
            trail = (await c.get(f"/api/v1/trails/{tid}")).json()
            module = trail["modules"][0]
            uid = module["units"][0]["unit"]["id"]
            job = (
                await c.post(
                    f"/api/v1/modules/{module['module']['id']}/generate",
                    json={
                        "unit_id": uid,
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                    },
                )
            ).json()
            done = await wait(c, job["id"])
            content = (
                await c.get(f"/api/v1/units/{uid}/versions/{done['result_id']}")
            ).json()
            mid = content["message"]["id"]
            source = (await c.get(f"/api/v1/messages/{mid}/clipping-source")).json()
            assert source["source"]["module_id"] == module["module"]["id"]
            assert source["source"]["content_version_id"] == done["result_id"]
            assert (
                "answer_key" not in str(source)
                and "Referência sintética" not in source["text"]
            )
            book_ids = []
            for scope in ({}, {"trail_id": tid}):
                book = (
                    await c.post(
                        "/api/v1/notebooks", json={"title": "Caderno de teste", **scope}
                    )
                ).json()
                book_ids.append(book["id"])
                page = (
                    await c.post(
                        f"/api/v1/notebooks/{book['id']}/pages",
                        json={"title": "Recorte da trilha"},
                    )
                ).json()
                clipped = await c.post(
                    f"/api/v1/pages/{page['id']}/clippings",
                    json={
                        "message_id": mid,
                        "start": 0,
                        "end": len(source["text"]),
                        "selected_text": source["text"],
                        "expected_version": 1,
                        "operation_id": str(uuid4()),
                    },
                )
                assert clipped.status_code == 201, clipped.text
            assert book_ids[0] != book_ids[1]
            wrong = await c.post(
                "/api/v1/notebooks",
                json={
                    "title": "Escopo inválido",
                    "trail_id": tid,
                    "topic_id": str(uuid4()),
                },
            )
            assert wrong.status_code == 422

    asyncio.run(scenario())
