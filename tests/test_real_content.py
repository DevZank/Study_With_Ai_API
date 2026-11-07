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
    reason="Defina STUDY_TEST_OLLAMA_MODEL para testar somente o Ollama local.",
)
def test_real_four_modes_and_exercise(database: Path) -> None:
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
                    "/api/v1/topics", json={"title": "Validação real do Marco 2"}
                )
            ).json()
            cid = (
                await client.post(
                    f"/api/v1/topics/{topic['id']}/conversations",
                    json={"title": "Aritmética"},
                )
            ).json()["id"]
            for mode in ["study", "memorize", "learn", "practice"]:
                response = await client.post(
                    f"/api/v1/conversations/{cid}/messages",
                    json={
                        "content": "Trabalhe apenas o conceito de somar 2 + 2. Seja breve e use no máximo dois blocos. Se houver exercício, use múltipla escolha com alternativas curtas.",
                        "model_id": MODEL,
                        "request_id": str(uuid4()),
                        "mode": mode,
                        "response_format": "blocks",
                    },
                )
                assert response.status_code == 202, response.text
                jid = response.json()["id"]
                for _ in range(1900):
                    job = (await client.get(f"/api/v1/jobs/{jid}")).json()
                    if job["status"] != "running":
                        break
                    await asyncio.sleep(0.1)
                assert job["status"] == "completed", job
                history = (
                    await client.get(f"/api/v1/conversations/{cid}/messages")
                ).json()
                message = history["items"][-1]
                assert message["document"]["mode"] == mode
                assert "answer_key" not in str(message)
                print(f"Modo {mode}: documento real validado.")
                if mode == "practice":
                    refs = [
                        b
                        for b in message["document"]["blocks"]
                        if b["type"] in ("quiz", "exercise")
                    ]
                    exercise_id = refs[0]["exercise_id"]
                    exercise = (
                        await client.get(f"/api/v1/exercises/{exercise_id}")
                    ).json()
                    assert exercise["solution"] is None
                    option = (
                        exercise["options"][0]["id"]
                        if exercise["kind"] == "multiple_choice"
                        else "true"
                        if exercise["kind"] == "true_false"
                        else "4"
                        if exercise["kind"] == "fill_blank"
                        else "Minha resposta para revisão."
                    )
                    attempt = await client.post(
                        f"/api/v1/exercises/{exercise_id}/attempts",
                        json={"response": option, "request_id": str(uuid4())},
                    )
                    assert attempt.status_code == 201, attempt.text
                    assert attempt.json()["score"] in (0, 1, None)
                    revealed = (
                        await client.get(f"/api/v1/exercises/{exercise_id}")
                    ).json()
                    assert revealed["solution"] is not None
                    if exercise["kind"] == "open":
                        assert attempt.json()["score"] is None
                    else:
                        assert attempt.json()["score"] == float(
                            option.strip().casefold()
                            == revealed["solution"].strip().casefold()
                        )
                    print(
                        "Exercício real: tentativa persistida e corrigida segundo o gabarito gerado."
                    )

    asyncio.run(scenario())
