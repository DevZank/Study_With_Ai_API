import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from content_fixture import generated, prompt_mode
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from test_chat import TestProvider

from study_api.application.chat import ChatService
from study_api.domain.chat import Job, Message
from study_api.domain.content import GeneratedDocument
from study_api.domain.exercises import Exercise
from study_api.infrastructure.db.database import engine_for
from study_api.infrastructure.db.repository import SqliteRepository
from study_api.main import create_app


class StructuredProvider(TestProvider):
    def __init__(self, invalid: bool = False) -> None:
        super().__init__()
        self.invalid = invalid
        self.calls = 0
        self.raw_seen = asyncio.Event()
        self.pause = False
        self.fail_first = False

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, object] | None = None,
    ) -> AsyncIterator[str]:
        self.calls += 1
        raw = (
            '{"answer_key":"SEGREDO_NAO_EXIBIR"'
            if self.invalid or (self.fail_first and self.calls == 1)
            else json.dumps(generated(prompt_mode(messages)), ensure_ascii=False)
        )
        self.raw_seen.set()
        yield raw[:15]
        if self.pause:
            await asyncio.sleep(10)
        yield raw[15:]


@pytest.mark.parametrize("mode", ["study", "memorize", "learn", "practice"])
def test_valid_modes(mode: str) -> None:
    assert GeneratedDocument.model_validate(generated(mode)).mode == mode


@pytest.mark.parametrize("change", ["version", "unknown", "answer", "ids", "shape"])
def test_reject_invalid(change: str) -> None:
    value = generated("practice")
    blocks = [b.model_dump() for b in GeneratedDocument.model_validate(value).blocks]
    if change == "version":
        value["schema_version"] = "99"
    elif change == "unknown":
        value["blocks"] = [
            {"id": "a", "type": "html", "html": "<script>alert(1)</script>"}
        ]
    elif change == "answer":
        value["blocks"] = [{**blocks[0], "answer_key": "z"}]
    elif change == "ids":
        value["blocks"] = [blocks[0], blocks[0]]
    else:
        value = {
            "schema_version": "1.0",
            "mode": "learn",
            "title": "Teste",
            "blocks": [
                {"id": "a", "type": "table", "columns": ["A", "B"], "rows": [["X"]]}
            ],
        }
    with pytest.raises(ValidationError):
        GeneratedDocument.model_validate(value)


async def create_conversation(client: AsyncClient) -> str:
    topic = (await client.post("/api/v1/topics", json={"title": "Tema"})).json()
    return str(
        (
            await client.post(
                f"/api/v1/topics/{topic['id']}/conversations",
                json={"title": "Conversa"},
            )
        ).json()["id"]
    )


async def wait_job(client: AsyncClient, job_id: str) -> dict[str, object]:
    for _ in range(100):
        result: dict[str, object] = (await client.get(f"/api/v1/jobs/{job_id}")).json()
        if result["status"] != "running":
            return result
        await asyncio.sleep(0.01)
    raise AssertionError("Geração não terminou no teste.")


def test_modes_protected_exercise_and_restart(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database, StructuredProvider())
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            cid = await create_conversation(client)
            for mode in ("study", "memorize", "learn", "practice"):
                changed = await client.patch(
                    f"/api/v1/conversations/{cid}", json={"active_mode": mode}
                )
                assert changed.json()["active_mode"] == mode
                sent = await client.post(
                    f"/api/v1/conversations/{cid}/messages",
                    json={
                        "content": "Matemática",
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                        "response_format": "blocks",
                        "mode": mode,
                    },
                )
                assert sent.status_code == 202, sent.text
                assert (await wait_job(client, sent.json()["id"]))[
                    "status"
                ] == "completed"
            history = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
            assert len(history["items"]) == 8
            assert [
                m["mode"] for m in history["items"] if m["role"] == "assistant"
            ] == ["study", "memorize", "learn", "practice"]
            public = history["items"][-1]
            assert "answer_key" not in json.dumps(history)
            assert "Referência sintética" not in json.dumps(history)
            exercise_id = public["document"]["blocks"][0]["exercise_id"]
            exercise = await client.get(f"/api/v1/exercises/{exercise_id}")
            assert exercise.json()["solution"] is None
            assert exercise.json()["explanation"] is None
            assert exercise.json()["hints"] == []
            assert (
                await client.get(f"/api/v1/exercises/{exercise_id}/attempts")
            ).json() == []
            hints = (await client.post(f"/api/v1/exercises/{exercise_id}/hints")).json()
            assert len(hints["hints"]) == 1 and hints["solution"] is None
            assert (
                await client.post(
                    f"/api/v1/exercises/{exercise_id}/attempts",
                    json={"response": "z", "request_id": str(uuid4())},
                )
            ).status_code == 422
            key = str(uuid4())
            wrong = await client.post(
                f"/api/v1/exercises/{exercise_id}/attempts",
                json={"response": "a", "request_id": key},
            )
            assert wrong.json()["score"] == 0
            duplicate = await client.post(
                f"/api/v1/exercises/{exercise_id}/attempts",
                json={"response": "a", "request_id": key},
            )
            assert duplicate.json()["id"] == wrong.json()["id"]
            right = await client.post(
                f"/api/v1/exercises/{exercise_id}/attempts",
                json={"response": "b", "request_id": str(uuid4())},
            )
            assert right.json()["score"] == 1
            assert (await client.get(f"/api/v1/exercises/{exercise_id}")).json()[
                "solution"
            ] == "b"
            stream = await client.get(f"/api/v1/jobs/{sent.json()['id']}/events")
            assert (
                "answer_key" not in stream.text
                and "Referência sintética" not in stream.text
            )
        restarted = create_app(database, StructuredProvider())
        async with (
            restarted.router.lifespan_context(restarted),
            AsyncClient(
                transport=ASGITransport(app=restarted), base_url="http://test"
            ) as client,
        ):
            assert (await client.get(f"/api/v1/conversations/{cid}")).json()[
                "active_mode"
            ] == "practice"
            assert (
                len(
                    (
                        await client.get(f"/api/v1/exercises/{exercise_id}/attempts")
                    ).json()
                )
                == 2
            )

    asyncio.run(scenario())


def test_repair_and_failed_commit_are_safe(
    database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def scenario() -> None:
        provider = StructuredProvider()
        provider.fail_first = True
        app = create_app(database, provider)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            cid = await create_conversation(client)
            sent = await client.post(
                f"/api/v1/conversations/{cid}/messages",
                json={
                    "content": "Teste",
                    "model_id": "local:test",
                    "request_id": str(uuid4()),
                    "response_format": "blocks",
                },
            )
            assert (await wait_job(client, sent.json()["id"]))["status"] == "completed"
            history = (await client.get(f"/api/v1/conversations/{cid}/messages")).json()
            assert history["items"][-1]["document"]
            assert history["items"][-1]["notice"]
            assert provider.calls == 2
            assert "SEGREDO_NAO_EXIBIR" not in json.dumps(history)

        engine = engine_for(database)
        repo = SqliteRepository(engine)
        original_save = repo.save_result

        def failed_commit(
            job: Job, message: Message, exercises: list[Exercise]
        ) -> None:
            if exercises:
                raise RuntimeError("Falha sintética de persistência.")
            original_save(job, message, exercises)

        monkeypatch.setattr(repo, "save_result", failed_commit)
        service = ChatService(repo, StructuredProvider())
        job = await service.start(
            cid, "Questão", "local:test", str(uuid4()), "practice", "blocks"
        )
        await asyncio.sleep(0.05)
        assert repo.job(job.id).status == "interrupted"
        assert repo.message(job.message_id).document_json == ""
        await service.close()
        engine.dispose()

    asyncio.run(scenario())


def test_invalid_json_and_cancel_never_publish_draft(database: Path) -> None:
    async def scenario() -> None:
        provider = StructuredProvider(invalid=True)
        app = create_app(database, provider)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            cid = await create_conversation(client)

            async def send() -> str:
                return str(
                    (
                        await client.post(
                            f"/api/v1/conversations/{cid}/messages",
                            json={
                                "content": "Teste",
                                "model_id": "local:test",
                                "request_id": str(uuid4()),
                                "response_format": "blocks",
                            },
                        )
                    ).json()["id"]
                )

            job_id = await send()
            assert (await wait_job(client, job_id))["status"] == "failed"
            assert provider.calls == 2
            history = await client.get(f"/api/v1/conversations/{cid}/messages")
            assert "SEGREDO_NAO_EXIBIR" not in history.text
            assert history.json()["items"][-1]["document"] is None
            provider.invalid = False
            provider.pause = True
            job_id = await send()
            await asyncio.sleep(0.02)
            history = await client.get(f"/api/v1/conversations/{cid}/messages")
            assert "schema_version" not in history.text
            assert (await client.post(f"/api/v1/jobs/{job_id}/cancel")).json()[
                "status"
            ] == "cancelled"

    asyncio.run(scenario())
