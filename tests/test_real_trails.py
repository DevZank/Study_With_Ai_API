"""Validação opcional com dados sintéticos enviados somente ao Ollama local."""

import asyncio
import json
import os
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from study_api.main import create_app

MODEL = os.environ.get("STUDY_TEST_OLLAMA_MODEL", "")


@pytest.mark.skipif(
    not MODEL, reason="Defina STUDY_TEST_OLLAMA_MODEL para usar o Ollama local."
)
def test_real_incremental_trail(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):

            async def operation(
                path: str, body: dict[str, object]
            ) -> dict[str, object]:
                response = await client.post(
                    "/api/v1" + path,
                    json={**body, "model_id": MODEL, "request_id": str(uuid4())},
                )
                assert response.status_code == 202, response.text
                for _ in range(2050):
                    job: dict[str, object] = (
                        await client.get("/api/v1/trail-jobs/" + response.json()["id"])
                    ).json()
                    if job["status"] != "running":
                        break
                    await asyncio.sleep(0.1)
                assert job["status"] == "completed", job
                return job

            topic = (
                await client.post(
                    "/api/v1/topics", json={"title": "Teste sintético de aritmética"}
                )
            ).json()
            plan = await operation(
                "/trails/plan",
                {
                    "topic_id": topic["id"],
                    "objective": "Aprender soma de números inteiros pequenos, com exemplos breves.",
                    "module_count": 5,
                },
            )
            trail = (await client.get(f"/api/v1/trails/{plan['result_id']}")).json()
            assert len(trail["modules"]) == 5
            assert all(not u["versions"] for m in trail["modules"] for u in m["units"])
            print("Plano real: cinco módulos, sem conteúdo antecipado.")
            first, second = trail["modules"][:2]
            uid = first["units"][0]["unit"]["id"]
            generated = await operation(
                f"/modules/{first['module']['id']}/generate", {"unit_id": uid}
            )
            await operation(
                f"/units/{uid}/complete",
                {
                    "version_id": generated["result_id"],
                    "difficulties": "Dúvida sintética sobre soma.",
                },
            )
            uid2 = second["units"][0]["unit"]["id"]
            next_unit = await operation(
                f"/modules/{second['module']['id']}/generate", {"unit_id": uid2}
            )
            view = (
                await client.get(
                    f"/api/v1/units/{uid2}/versions/{next_unit['result_id']}"
                )
            ).json()
            assert (
                len(json.loads(view["version"]["context"])["previous_summaries"]) == 1
            )
            assert "answer_key" not in str(view)
            final = (await client.get(f"/api/v1/trails/{plan['result_id']}")).json()
            assert all(
                not u["versions"] for m in final["modules"][2:] for u in m["units"]
            )
            print(
                "Duas unidades reais sob demanda; segunda com resumo persistido da primeira."
            )

    asyncio.run(scenario())
