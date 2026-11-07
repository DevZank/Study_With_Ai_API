import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from study_api.main import create_app

MODEL = os.environ.get("STUDY_TEST_OLLAMA_MODEL", "")


@pytest.mark.skipif(
    not MODEL,
    reason="Defina STUDY_TEST_OLLAMA_MODEL para autorizar o teste local real.",
)
def test_real_response_cancel_restart(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            topic = (
                await client.post(
                    "/api/v1/topics", json={"title": "Validação local real"}
                )
            ).json()
            conversation = (
                await client.post(
                    f"/api/v1/topics/{topic['id']}/conversations",
                    json={"title": "Teste real"},
                )
            ).json()
            cid = conversation["id"]
            started = await client.post(
                f"/api/v1/conversations/{cid}/messages",
                json={
                    "content": "Responda em uma frase: quanto é dois mais dois?",
                    "model_id": MODEL,
                    "request_id": str(uuid4()),
                },
            )
            assert started.status_code == 202, started.text
            jid = started.json()["id"]
            for _ in range(1700):
                job = (await client.get(f"/api/v1/jobs/{jid}")).json()
                if job["status"] != "running":
                    break
                await asyncio.sleep(0.1)
            assert job["status"] == "completed", job
            history = (
                await client.get(f"/api/v1/conversations/{cid}/messages")
            ).json()["items"]
            assert history[-1]["content"].strip()
            next_turn = await client.post(
                f"/api/v1/conversations/{cid}/messages",
                json={
                    "content": "Escreva uma explicação longa, de mil palavras, sobre números inteiros.",
                    "model_id": MODEL,
                    "request_id": str(uuid4()),
                },
            )
            assert next_turn.status_code == 202, next_turn.text
            second = next_turn.json()["id"]
            for _ in range(600):
                partial = (
                    await client.get(f"/api/v1/conversations/{cid}/messages")
                ).json()["items"][-1]
                if partial["content"]:
                    break
                await asyncio.sleep(0.1)
            cancelled = await client.post(f"/api/v1/jobs/{second}/cancel")
            assert cancelled.json()["status"] == "cancelled", cancelled.text
        restarted = create_app(database)
        async with (
            restarted.router.lifespan_context(restarted),
            AsyncClient(
                transport=ASGITransport(app=restarted), base_url="http://test"
            ) as client,
        ):
            history = (
                await client.get(f"/api/v1/conversations/{cid}/messages")
            ).json()["items"]
            assert len(history) == 4
            assert history[1]["status"] == "completed"
            assert history[-1]["status"] == "cancelled"

    asyncio.run(scenario())
