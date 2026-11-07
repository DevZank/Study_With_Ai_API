import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect

from study_api.application.chat import ChatService
from study_api.domain.chat import AppError, Conversation, Job, Message, Topic
from study_api.infrastructure.db.database import engine_for
from study_api.infrastructure.db.models import Base
from study_api.infrastructure.db.repository import SqliteRepository
from study_api.main import create_app


class TestProvider:
    __test__ = False

    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode
        self.closed = False

    async def models(self) -> list[str]:
        return ["local:test"]

    async def validate_model(self, model: str) -> None:
        if model != "local:test":
            raise AppError("MODEL_UNAVAILABLE", "Modelo indisponível.", 422)

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, object] | None = None,
    ) -> AsyncIterator[str]:
        try:
            yield "Parte inicial"
            if self.mode == "wait":
                await asyncio.sleep(10)
            if self.mode == "fail":
                raise AppError("STREAM_INTERRUPTED", "Transmissão interrompida.", 502)
            yield " e conclusão."
        finally:
            self.closed = True


def test_migration_and_persistence(database: Path) -> None:
    engine = engine_for(database)
    with engine.connect() as connection:
        assert (
            compare_metadata(MigrationContext.configure(connection), Base.metadata)
            == []
        )
    assert {
        "topics",
        "messages",
        "conversations",
        "profiles",
        "generation_jobs",
    } <= set(inspect(engine).get_table_names())
    repo = SqliteRepository(engine)
    topic = repo.save_topic(Topic("Biologia"))
    conversation = repo.save_conversation(Conversation(topic.id))
    repo.save_message(Message(conversation.id, "user", "O que é uma célula?"))
    engine.dispose()
    second = engine_for(database)
    restored = SqliteRepository(second)
    assert restored.topic(topic.id).title == "Biologia"
    assert restored.messages(conversation.id)[0].content == "O que é uma célula?"
    second.dispose()


def test_api_lifecycle(database: Path) -> None:
    async def scenario() -> None:
        provider = TestProvider()
        app = create_app(database, provider)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            assert (
                await client.post("/api/v1/topics", json={"title": " "})
            ).status_code == 422
            assert (
                await client.post(
                    "/api/v1/topics",
                    json={"title": "X"},
                    headers={"Origin": "https://untrusted.example"},
                )
            ).status_code == 403
            assert (
                await client.post("/api/v1/topics", content=b"x" * 40000)
            ).status_code == 413
            topic = (
                await client.post("/api/v1/topics", json={"title": "Física"})
            ).json()
            topic_id = topic["id"]
            await client.patch(
                f"/api/v1/topics/{topic_id}", json={"title": "Física básica"}
            )
            conversation = (
                await client.post(
                    f"/api/v1/topics/{topic_id}/conversations",
                    json={"title": "Primeira"},
                )
            ).json()
            cid = conversation["id"]
            body = {
                "content": "Explique massa.",
                "model_id": "local:test",
                "request_id": str(uuid4()),
            }
            result = await client.post(
                f"/api/v1/conversations/{cid}/messages", json=body
            )
            assert result.status_code == 202
            job = result.json()
            await asyncio.sleep(0.05)
            duplicate = await client.post(
                f"/api/v1/conversations/{cid}/messages", json=body
            )
            assert duplicate.json()["id"] == job["id"]
            conflict = await client.post(
                f"/api/v1/conversations/{cid}/messages",
                json={**body, "content": "Outra"},
            )
            assert conflict.status_code == 409
            stream = await client.get(f"/api/v1/jobs/{job['id']}/events")
            assert "event: job.completed" in stream.text
            history = (
                await client.get(f"/api/v1/conversations/{cid}/messages")
            ).json()["items"]
            assert len(history) == 2
            assert history[-1]["content"] == "Parte inicial e conclusão."
            page = (
                await client.get(f"/api/v1/conversations/{cid}/messages?limit=1")
            ).json()
            second = (
                await client.get(
                    f"/api/v1/conversations/{cid}/messages?cursor={page['next_cursor']}"
                )
            ).json()
            assert second["items"][0]["role"] == "assistant"
            await client.patch(
                f"/api/v1/topics/{topic_id}", json={"status": "archived"}
            )
            assert (
                await client.post(
                    f"/api/v1/conversations/{cid}/messages",
                    json={**body, "request_id": str(uuid4())},
                )
            ).status_code == 409
            await client.delete(f"/api/v1/topics/{topic_id}")
            assert (await client.get("/api/v1/topics")).json()["items"] == []
            await client.patch(f"/api/v1/topics/{topic_id}", json={"status": "active"})
            assert (
                len(
                    (await client.get(f"/api/v1/conversations/{cid}/messages")).json()[
                        "items"
                    ]
                )
                == 2
            )
        restarted = create_app(database, TestProvider())
        async with (
            restarted.router.lifespan_context(restarted),
            AsyncClient(
                transport=ASGITransport(app=restarted), base_url="http://test"
            ) as client,
        ):
            assert (
                len(
                    (await client.get(f"/api/v1/conversations/{cid}/messages")).json()[
                        "items"
                    ]
                )
                == 2
            )

    asyncio.run(scenario())


def test_concurrency_limits_and_immediate_cancel(database: Path) -> None:
    async def scenario() -> None:
        engine = engine_for(database)
        repo = SqliteRepository(engine)
        topic = repo.save_topic(Topic("Concorrência"))
        conversation = repo.save_conversation(Conversation(topic.id))
        service = ChatService(repo, TestProvider("wait"))
        with pytest.raises(AppError, match="Modelo indisponível"):
            await service.start(
                conversation.id, "Não persistir", "ausente", str(uuid4())
            )
        assert repo.messages(conversation.id) == []
        first = await service.start(
            conversation.id, "Teste", "local:test", str(uuid4())
        )
        with pytest.raises(AppError, match="Aguarde ou cancele"):
            await service.start(
                conversation.id, "Duplicada", "local:test", str(uuid4())
            )
        await service.cancel(first.id)
        assert repo.job(first.id).status == "cancelled"
        assert len(repo.messages(conversation.id)) == 2
        for _ in range(30):
            repo.save_message(Message(conversation.id, "user", "Histórico"))
        with pytest.raises(AppError, match="limite inicial"):
            await service.start(
                conversation.id, "Acima do limite", "local:test", str(uuid4())
            )
        await service.close()
        engine.dispose()

    asyncio.run(scenario())


def test_cancel_failure_and_recovery(database: Path) -> None:
    async def scenario() -> None:
        engine = engine_for(database)
        repo = SqliteRepository(engine)
        topic = repo.save_topic(Topic("Teste"))
        conversation = repo.save_conversation(Conversation(topic.id))
        provider = TestProvider("wait")
        service = ChatService(repo, provider)
        job = await service.start(conversation.id, "Teste", "local:test", str(uuid4()))
        await asyncio.sleep(0.02)
        cancelled = await service.cancel(job.id)
        assert cancelled.status == "cancelled"
        assert repo.message(job.message_id).content == "Parte inicial"
        assert provider.closed
        assert not service.tasks
        service.provider = TestProvider("fail")
        failure = await service.start(
            conversation.id, "Teste falha", "local:test", str(uuid4())
        )
        await asyncio.sleep(0.02)
        assert repo.job(failure.id).status == "failed"
        assert repo.message(failure.message_id).content == "Parte inicial"
        interrupted = Message(
            conversation.id, "assistant", "Texto recuperável", status="running"
        )
        user = Message(conversation.id, "user", "Antes do reinício")
        pending = Job(
            conversation.id, interrupted.id, "local:test", str(uuid4()), "hash"
        )
        repo.create_turn(user, interrupted, pending)
        ChatService(repo, TestProvider()).recover()
        assert repo.job(pending.id).status == "interrupted"
        assert repo.message(interrupted.id).content == "Texto recuperável"
        await service.close()
        engine.dispose()

    asyncio.run(scenario())
