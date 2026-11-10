"""Testes determinísticos de FSRS, flashcards, métricas pedagógicas e gamificação."""

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from test_content import StructuredProvider
from test_trails import TrailProvider, planned, wait

from study_api.domain.progress import (
    ReviewState,
    retrievability_at,
    schedule_review,
)
from study_api.main import create_app


def test_fsrs_deterministic_scheduling_and_decay() -> None:
    t0 = "2026-11-10T10:00:00+00:00"
    initial = ReviewState(
        id="state-1",
        flashcard_id="card-1",
        topic_id="topic-1",
        due_at=t0,
        created_at=t0,
        updated_at=t0,
    )
    # Primeira revisão com nota 3 (Bom): estabilidade inicial w_2 = 3.2 dias, intervalo = 3.2 dias.
    s1, e1 = schedule_review(initial, 3, t0, "req-1")
    assert s1.reps == 1
    assert s1.lapses == 0
    assert s1.state == "review"
    assert s1.stability == pytest.approx(3.2)
    assert e1.was_due is True
    assert e1.scheduled_days == pytest.approx(3.2)
    assert s1.due_at == "2026-11-13T14:48:00+00:00"

    # Na marca exata de t = S dias (3,2 dias depois), a retenção FSRS R(S, S) é 0.9 (90%).
    assert retrievability_at(s1, "2026-11-13T14:48:00+00:00") == pytest.approx(
        0.9, abs=1e-3
    )
    # Após 10 dias sem revisar, a retenção estimada cai de forma determinística.
    r_10d = retrievability_at(s1, "2026-11-20T10:00:00+00:00")
    assert r_10d is not None and r_10d < 0.8

    # Segunda revisão no vencimento com nota 4 (Fácil) amplia a estabilidade.
    s2, e2 = schedule_review(s1, 4, "2026-11-13T14:48:00+00:00", "req-2")
    assert s2.reps == 2
    assert s2.lapses == 0
    assert s2.stability > s1.stability
    assert e2.elapsed_days == pytest.approx(3.2)

    # Um lapso (nota 1 = Errei) reduz estabilidade, incrementa lapses e agenda reforço curto (0,25 dia = 6h).
    s3, e3 = schedule_review(s2, 1, "2026-11-30T14:48:00+00:00", "req-3")
    assert s3.reps == 3
    assert s3.lapses == 1
    assert s3.state == "relearning"
    assert s3.stability < s2.stability
    assert e3.scheduled_days == pytest.approx(0.25)
    assert s3.due_at == "2026-11-30T20:48:00+00:00"


def test_flashcards_reviews_metrics_gamification_and_restart(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database, StructuredProvider())
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c,
        ):
            topic = (
                await c.post("/api/v1/topics", json={"title": "Algoritmos"})
            ).json()
            tid = topic["id"]
            conv = (
                await c.post(
                    f"/api/v1/topics/{tid}/conversations",
                    json={"title": "Sessão de estudo"},
                )
            ).json()
            cid = conv["id"]

            # 1. Gera resposta no modo Memorizar e importa bloco flashcard com proveniência.
            job_mem = (
                await c.post(
                    f"/api/v1/conversations/{cid}/messages",
                    json={
                        "content": "Cartão sobre busca binária",
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                        "mode": "memorize",
                        "response_format": "blocks",
                    },
                )
            ).json()
            while (await c.get(f"/api/v1/jobs/{job_mem['id']}")).json()[
                "status"
            ] == "running":
                await asyncio.sleep(0.02)
            msgs = (await c.get(f"/api/v1/conversations/{cid}/messages")).json()[
                "items"
            ]
            assistant_mem = msgs[-1]
            import_op = str(uuid4())
            imported = await c.post(
                f"/api/v1/messages/{assistant_mem['id']}/flashcards",
                json={
                    "block_id": "f1",
                    "concept_name": "Busca Binária",
                    "operation_id": import_op,
                },
            )
            assert imported.status_code == 201, imported.text
            imported_card = imported.json()["card"]
            assert imported_card["source_type"] == "message_block"
            assert imported_card["source_ref"]["message_id"] == assistant_mem["id"]
            # Repetir importação do mesmo bloco é idempotente e não duplica cartão.
            dup_import = await c.post(
                f"/api/v1/messages/{assistant_mem['id']}/flashcards",
                json={
                    "block_id": "f1",
                    "concept_name": "Busca Binária",
                    "operation_id": str(uuid4()),
                },
            )
            assert dup_import.status_code == 201
            assert dup_import.json()["card"]["id"] == imported_card["id"]

            # 2. Cria cartão manual determinístico com timestamp fixo.
            t0 = "2026-11-10T12:00:00+00:00"
            create_op = str(uuid4())
            created = await c.post(
                f"/api/v1/topics/{tid}/flashcards",
                json={
                    "front": "Qual a complexidade da busca binária?",
                    "back": "O(log n) em vetor ordenado.",
                    "concept_name": "Busca Binária",
                    "operation_id": create_op,
                    "created_at": t0,
                },
            )
            assert created.status_code == 201, created.text
            card_id = created.json()["card"]["id"]
            # Conflito de idempotência ao reutilizar operation_id com outro texto.
            conflict_op = await c.post(
                f"/api/v1/topics/{tid}/flashcards",
                json={
                    "front": "Outro texto",
                    "back": "Outro verso",
                    "concept_name": "Busca Binária",
                    "operation_id": create_op,
                },
            )
            assert conflict_op.status_code == 409

            # 3. Revisão FSRS determinística: cartão vence em t0, após nota 3 agenda para +3,2 dias.
            due_before = (
                await c.get("/api/v1/reviews/due", params={"topic_id": tid, "at": t0})
            ).json()
            assert any(item["card"]["id"] == card_id for item in due_before)

            grade_req = str(uuid4())
            graded = await c.post(
                f"/api/v1/reviews/{card_id}/grade",
                json={
                    "rating": 3,
                    "request_id": grade_req,
                    "reviewed_at": t0,
                },
            )
            assert graded.status_code == 200, graded.text
            g_data = graded.json()
            assert g_data["review_state"]["reps"] == 1
            assert g_data["review_state"]["due_at"] == "2026-11-13T16:48:00+00:00"
            assert g_data["event"]["xp_awarded"] == 10

            # Idempotência de revisão com o mesmo request_id.
            graded_again = await c.post(
                f"/api/v1/reviews/{card_id}/grade",
                json={
                    "rating": 3,
                    "request_id": grade_req,
                    "reviewed_at": t0,
                },
            )
            assert graded_again.status_code == 200
            assert graded_again.json()["review_state"]["reps"] == 1

            # Em t0 + 1 hora, o cartão não está mais vencido.
            due_after = (
                await c.get(
                    f"/api/v1/reviews/due?topic_id={tid}&at=2026-11-10T13:00:00%2B00:00"
                )
            ).json()
            assert all(item["card"]["id"] != card_id for item in due_after)

            # Anti-farming: revisar antecipadamente antes do vencimento não concede XP extra.
            early_grade = await c.post(
                f"/api/v1/reviews/{card_id}/grade",
                json={
                    "rating": 4,
                    "request_id": str(uuid4()),
                    "reviewed_at": "2026-11-10T14:00:00+00:00",
                },
            )
            assert early_grade.status_code == 200
            assert early_grade.json()["event"]["was_due"] is False
            assert early_grade.json()["event"]["xp_awarded"] == 0

            # 4. Editar o texto do cartão preserva estado FSRS (reps=2) e histórico.
            edit_op = str(uuid4())
            edited = await c.patch(
                f"/api/v1/flashcards/{card_id}",
                json={
                    "front": "Qual a complexidade temporal da busca binária?",
                    "back": "O(log n) no pior caso em coleção ordenada.",
                    "concept_name": "Busca Binária",
                    "archived": False,
                    "expected_version": 1,
                    "operation_id": edit_op,
                },
            )
            assert edited.status_code == 200, edited.text
            assert edited.json()["card"]["version"] == 2
            assert edited.json()["review_state"]["reps"] == 2
            # Versão antiga retorna 409 FLASHCARD_CONFLICT.
            stale_edit = await c.patch(
                f"/api/v1/flashcards/{card_id}",
                json={
                    "front": "Conflito",
                    "back": "Conflito",
                    "concept_name": "Busca Binária",
                    "archived": False,
                    "expected_version": 1,
                    "operation_id": str(uuid4()),
                },
            )
            assert stale_edit.status_code == 409

            # 5. Praticar exercício registra domínio e XP sem premiar tentativas repetidas (anti-farming).
            job_prac = (
                await c.post(
                    f"/api/v1/conversations/{cid}/messages",
                    json={
                        "content": "Exercício sobre busca binária",
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                        "mode": "practice",
                        "response_format": "blocks",
                    },
                )
            ).json()
            while (await c.get(f"/api/v1/jobs/{job_prac['id']}")).json()[
                "status"
            ] == "running":
                await asyncio.sleep(0.02)
            msgs_prac = (await c.get(f"/api/v1/conversations/{cid}/messages")).json()[
                "items"
            ]
            ex_id = msgs_prac[-1]["document"]["blocks"][0]["exercise_id"]

            att1 = await c.post(
                f"/api/v1/exercises/{ex_id}/attempts",
                json={"response": "b", "request_id": str(uuid4())},
            )
            assert att1.status_code == 201
            assert att1.json()["score"] == 1.0

            prog1 = (
                await c.get(
                    f"/api/v1/progress/topics/{tid}?at=2026-11-11T14:00:00%2B00:00"
                )
            ).json()
            xp_after_first = prog1["gamification"]["total_xp"]
            # 10 XP (revisão no prazo) + 5 XP (primeira tentativa) + 15 XP (exercício correto) = 30 XP
            assert xp_after_first == 30

            # Repetir resposta correta no mesmo exercício NÃO soma XP extra.
            att2 = await c.post(
                f"/api/v1/exercises/{ex_id}/attempts",
                json={"response": "b", "request_id": str(uuid4())},
            )
            assert att2.status_code == 201
            prog2 = (
                await c.get(
                    f"/api/v1/progress/topics/{tid}?at=2026-11-11T14:00:00%2B00:00"
                )
            ).json()
            assert prog2["gamification"]["total_xp"] == xp_after_first

            # Verifica separação dos três indicadores pedagógicos:
            # Sem trilha concluída, completion_ratio é None, mas mastery e retention possuem valores reais!
            assert prog2["completion"]["completed_units"] == 0
            assert prog2["completion"]["completion_ratio"] is None
            assert prog2["mastery"]["estimated_score"] is not None
            assert prog2["mastery"]["estimated_score"] > 0.7
            assert prog2["retention"]["estimated_retention"] is not None
            assert prog2["retention"]["reviewed_cards"] == 1
            assert "completion" in prog2["explanations"]
            assert "mastery" in prog2["explanations"]
            assert "retention" in prog2["explanations"]

            # Conquistas desbloqueadas até aqui: first_practice, accurate_practice, first_review, consistent_learner
            earned_codes = {
                a["code"] for a in prog2["gamification"]["achievements"] if a["earned"]
            }
            assert {
                "first_practice",
                "accurate_practice",
                "first_review",
                "consistent_learner",
            } <= earned_codes

            # Preferência de ocultar gamificação.
            pref = await c.patch(
                "/api/v1/progress/preferences", json={"hide_gamification": True}
            )
            assert pref.status_code == 200
            assert pref.json()["hide_gamification"] is True

        # 6. Reinicia a aplicação sobre o mesmo banco SQLite e verifica persistência completa.
        restarted = create_app(database, StructuredProvider())
        async with (
            restarted.router.lifespan_context(restarted),
            AsyncClient(
                transport=ASGITransport(app=restarted), base_url="http://test"
            ) as c,
        ):
            history = (await c.get(f"/api/v1/flashcards/{card_id}/history")).json()
            assert len(history) == 2
            cards = (await c.get(f"/api/v1/topics/{tid}/flashcards")).json()
            saved_card = next(x for x in cards if x["card"]["id"] == card_id)
            assert saved_card["review_state"]["reps"] == 2
            overview = (await c.get("/api/v1/progress/overview")).json()
            assert overview["gamification"]["total_xp"] == 30
            assert overview["gamification"]["hide_gamification"] is True

    asyncio.run(scenario())


def test_trail_progress_and_unit_completion_xp_anti_farming(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database, TrailProvider())
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c,
        ):
            trail_id = await planned(c)
            trail_view = (await c.get(f"/api/v1/trails/{trail_id}")).json()
            topic_id = trail_view["trail"]["topic_id"]
            module = trail_view["modules"][0]
            unit_id = module["units"][0]["unit"]["id"]

            # Antes de gerar ou concluir unidades: progresso 0/total_units, sem XP de trilha.
            initial_prog = (await c.get(f"/api/v1/progress/topics/{topic_id}")).json()
            assert initial_prog["completion"]["completed_units"] == 0
            assert (
                initial_prog["completion"]["total_units"] == trail_view["total_units"]
            )
            assert initial_prog["gamification"]["total_xp"] == 0

            # Gera e conclui a primeira unidade.
            gen_job = (
                await c.post(
                    f"/api/v1/modules/{module['module']['id']}/generate",
                    json={
                        "unit_id": unit_id,
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                    },
                )
            ).json()
            gen_done = await wait(c, gen_job["id"])
            comp_job = (
                await c.post(
                    f"/api/v1/units/{unit_id}/complete",
                    json={
                        "version_id": gen_done["result_id"],
                        "difficulties": "Nenhuma",
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                    },
                )
            ).json()
            await wait(c, comp_job["id"])

            after_first = (await c.get(f"/api/v1/progress/topics/{topic_id}")).json()
            assert after_first["completion"]["completed_units"] == 1
            assert after_first["gamification"]["total_xp"] == 25
            earned = {
                a["code"]
                for a in after_first["gamification"]["achievements"]
                if a["earned"]
            }
            assert "trail_step" in earned

            # Regenerar uma segunda versão da MESMA unidade e concluí-la não duplica XP da unidade.
            regen_job = (
                await c.post(
                    f"/api/v1/modules/{module['module']['id']}/generate",
                    json={
                        "unit_id": unit_id,
                        "force_regenerate": True,
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                    },
                )
            ).json()
            regen_done = await wait(c, regen_job["id"])
            comp_job2 = (
                await c.post(
                    f"/api/v1/units/{unit_id}/complete",
                    json={
                        "version_id": regen_done["result_id"],
                        "difficulties": "Revisão extra",
                        "model_id": "local:test",
                        "request_id": str(uuid4()),
                    },
                )
            ).json()
            await wait(c, comp_job2["id"])

            after_regen = (await c.get(f"/api/v1/progress/topics/{topic_id}")).json()
            assert after_regen["gamification"]["total_xp"] == 25

    asyncio.run(scenario())
