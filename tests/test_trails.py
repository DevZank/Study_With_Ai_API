import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from httpx import ASGITransport, AsyncClient
from test_chat import TestProvider
from trail_fixture import lesson_payload, plan_payload, summary_payload

from study_api.domain.trails import (
    TrailJob,
)
from study_api.infrastructure.db.database import engine_for
from study_api.infrastructure.db.trails import SqliteTrails
from study_api.main import create_app


class TrailProvider(TestProvider):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[list[dict[str, str]]] = []
        self.slow = False
        self.invalid = False

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_schema: dict[str, object] | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(messages)
        title = response_schema.get("title") if response_schema else None
        if title == "GeneratedPlan":
            value = plan_payload()
        elif title == "GeneratedSummary":
            value = summary_payload()
        else:
            value = lesson_payload()
        raw = (
            json.dumps(value, ensure_ascii=False)
            if not self.invalid
            else '{"unexpected":"INVALID_PLAN"}'
        )
        yield raw[:20]
        if self.slow:
            await asyncio.sleep(10)
        yield raw[20:]


async def wait(client: AsyncClient, job_id: str) -> dict[str, object]:
    for _ in range(200):
        result: dict[str, object] = (
            await client.get(f"/api/v1/trail-jobs/{job_id}")
        ).json()
        if result["status"] != "running":
            return result
        await asyncio.sleep(0.01)
    raise AssertionError("Operação não terminou no teste.")


async def planned(client: AsyncClient) -> str:
    topic = (
        await client.post("/api/v1/topics", json={"title": "Tema de trilha"})
    ).json()
    result = await client.post(
        "/api/v1/trails/plan",
        json={
            "topic_id": topic["id"],
            "objective": "Aprender soma",
            "prior_knowledge": "Iniciante",
            "module_count": 5,
            "model_id": "local:test",
            "request_id": str(uuid4()),
        },
    )
    assert result.status_code == 202, result.text
    job = await wait(client, result.json()["id"])
    assert job["status"] == "completed", job
    return str(job["result_id"])


def test_incremental_cache_versions_summary_and_restart(database: Path) -> None:
    async def scenario() -> None:
        provider = TrailProvider()
        app = create_app(database, provider)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            tid = await planned(client)
            value = (await client.get(f"/api/v1/trails/{tid}")).json()
            assert len(value["modules"]) == 5 and value["total_units"] == 6
            assert len(provider.calls) == 1
            assert all(not u["versions"] for m in value["modules"] for u in m["units"])
            first = value["modules"][0]
            second = value["modules"][1]
            uid = first["units"][0]["unit"]["id"]
            mid = first["module"]["id"]
            body = {
                "model_id": "local:test",
                "request_id": str(uuid4()),
                "unit_id": uid,
            }
            response = await client.post(f"/api/v1/modules/{mid}/generate", json=body)
            job = await wait(client, response.json()["id"])
            assert job["status"] == "completed", job
            version_id = str(job["result_id"])
            content = (
                await client.get(f"/api/v1/units/{uid}/versions/{version_id}")
            ).json()
            assert "answer_key" not in str(content)
            exercise = next(
                b
                for b in content["message"]["document"]["blocks"]
                if b["type"] in {"quiz", "exercise"}
            )
            attempt = await client.post(
                f"/api/v1/exercises/{exercise['exercise_id']}/attempts",
                json={"response": "b", "request_id": str(uuid4())},
            )
            assert attempt.status_code == 201
            duplicate = await client.post(f"/api/v1/modules/{mid}/generate", json=body)
            assert duplicate.json()["id"] == response.json()["id"]
            calls = len(provider.calls)
            cached = await client.post(
                f"/api/v1/modules/{mid}/generate",
                json={**body, "request_id": str(uuid4())},
            )
            assert (await wait(client, cached.json()["id"]))["cached"] is True
            assert len(provider.calls) == calls
            value = (await client.get(f"/api/v1/trails/{tid}")).json()
            assert len(value["modules"][0]["units"][0]["versions"]) == 1
            assert all(
                not u["versions"] for m in value["modules"][1:] for u in m["units"]
            )
            complete = await client.post(
                f"/api/v1/units/{uid}/complete",
                json={
                    "version_id": version_id,
                    "difficulties": "Dúvida informada pelo aluno",
                    "model_id": "local:test",
                    "request_id": str(uuid4()),
                },
            )
            summary_job = await wait(client, complete.json()["id"])
            assert summary_job["status"] == "completed", summary_job
            value = (await client.get(f"/api/v1/trails/{tid}")).json()
            assert value["completed_units"] == 1
            summary = value["modules"][0]["units"][0]["summaries"][0]
            assert summary["objective_attempts"] == 1
            assert summary["mastery_estimate"] is None
            second_uid = second["units"][0]["unit"]["id"]
            second_job = await client.post(
                f"/api/v1/modules/{second['module']['id']}/generate",
                json={
                    "unit_id": second_uid,
                    "model_id": "local:test",
                    "request_id": str(uuid4()),
                },
            )
            second_done = await wait(client, second_job.json()["id"])
            assert second_done["status"] == "completed", second_done
            view = (
                await client.get(
                    f"/api/v1/units/{second_uid}/versions/{second_done['result_id']}"
                )
            ).json()
            context = json.loads(view["version"]["context"])
            assert len(context["previous_summaries"]) == 1
            assert (
                context["previous_summaries"][0]["difficulties"]
                == "Dúvida informada pelo aluno"
            )
            assert "RESUMOS_ANTERIORES_JSON" in provider.calls[-1][-1]["content"]
            assert all(len(messages) == 2 for messages in provider.calls)
            force = await client.post(
                f"/api/v1/modules/{mid}/generate",
                json={**body, "request_id": str(uuid4()), "force_regenerate": True},
            )
            assert (await wait(client, force.json()["id"]))["status"] == "completed"
            versions = (await client.get(f"/api/v1/trails/{tid}")).json()["modules"][0][
                "units"
            ][0]["versions"]
            assert len(versions) == 2
            old = (
                await client.get(f"/api/v1/units/{uid}/versions/{version_id}")
            ).json()
            assert old["summaries"] and old["message"]["document"]
        restarted = create_app(database, TrailProvider())
        async with (
            restarted.router.lifespan_context(restarted),
            AsyncClient(
                transport=ASGITransport(app=restarted), base_url="http://test"
            ) as client,
        ):
            restored = (await client.get(f"/api/v1/trails/{tid}")).json()
            assert len(restored["modules"][0]["units"][0]["versions"]) == 2
            assert all(
                not u["versions"] for m in restored["modules"][2:] for u in m["units"]
            )

    asyncio.run(scenario())


def test_edit_conflict_archive_cancel_invalid_recover(database: Path) -> None:
    async def scenario() -> None:
        provider = TrailProvider()
        app = create_app(database, provider)
        async with (
            app.router.lifespan_context(app),
            AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            tid = await planned(client)
            value = (await client.get(f"/api/v1/trails/{tid}")).json()
            ids = [m["module"]["id"] for m in value["modules"]]
            order = await client.patch(
                f"/api/v1/trails/{tid}/modules/order",
                json={"expected_version": 1, "module_ids": list(reversed(ids))},
            )
            assert order.status_code == 200
            assert [m["module"]["id"] for m in order.json()["modules"]] == list(
                reversed(ids)
            )
            stale = await client.patch(
                f"/api/v1/trails/{tid}",
                json={"expected_version": 1, "title": "Não deve salvar"},
            )
            assert stale.status_code == 409
            archived = await client.patch(
                f"/api/v1/modules/{ids[0]}",
                json={"expected_version": 2, "archived": True},
            )
            assert archived.status_code == 200
            assert any(m["module"]["archived"] for m in archived.json()["modules"])
            module_plan = archived.json()["modules"][0]["module"]["plan"]
            module_plan["title"] = "Título editado"
            edited = await client.patch(
                f"/api/v1/modules/{ids[-1]}",
                json={"expected_version": 3, "plan": module_plan},
            )
            assert edited.status_code == 200
            added = await client.post(
                f"/api/v1/trails/{tid}/modules",
                json={"expected_version": 4, "plan": module_plan},
            )
            assert added.status_code == 201
            persisted = (await client.get(f"/api/v1/trails/{tid}")).json()
            assert persisted["trail"]["version"] == 5
            assert len(persisted["modules"]) == 6
            assert (
                persisted["modules"][0]["module"]["plan"]["title"] == "Título editado"
            )
            provider.slow = True
            module = archived.json()["modules"][0]
            started = await client.post(
                f"/api/v1/modules/{module['module']['id']}/generate",
                json={"model_id": "local:test", "request_id": str(uuid4())},
            )
            await asyncio.sleep(0.03)
            cancelled = await client.post(
                f"/api/v1/trail-jobs/{started.json()['id']}/cancel"
            )
            assert cancelled.json()["status"] == "cancelled"
            assert all(
                not u["versions"]
                for m in (await client.get(f"/api/v1/trails/{tid}")).json()["modules"]
                for u in m["units"]
            )
            provider.slow = False
            provider.invalid = True
            topic = (
                await client.post("/api/v1/topics", json={"title": "Plano inválido"})
            ).json()
            invalid = await client.post(
                "/api/v1/trails/plan",
                json={
                    "topic_id": topic["id"],
                    "objective": "Teste",
                    "model_id": "local:test",
                    "request_id": str(uuid4()),
                },
            )
            assert (await wait(client, invalid.json()["id"]))["status"] == "failed"
            assert (await client.get(f"/api/v1/topics/{topic['id']}/trails")).json()[
                "items"
            ] == []
        engine = engine_for(database)
        repo = SqliteTrails(engine)
        pending = TrailJob(
            kind="plan",
            target_id="pending",
            model_id="local:test",
            request_id=str(uuid4()),
            fingerprint="f",
        )
        repo.commit([pending])
        engine.dispose()
        restarted = create_app(database, TrailProvider())
        async with restarted.router.lifespan_context(restarted):
            assert (
                restarted.state.trails.repo.get(TrailJob, pending.id).status
                == "interrupted"
            )

    asyncio.run(scenario())
