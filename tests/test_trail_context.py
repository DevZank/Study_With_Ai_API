"""Verifica o orçamento e a seleção de resumos, sem chamar modelos."""

import asyncio
import json
from pathlib import Path

from test_trails import TrailProvider

from study_api.domain.chat import Conversation, Message, Topic
from study_api.domain.trails import (
    ContentVersion,
    GeneratedSummary,
    LearningSummary,
    Module,
    ModulePlan,
    Trail,
    Unit,
)
from study_api.main import create_app


def test_context_budget_and_only_preceding_units(database: Path) -> None:
    async def scenario() -> None:
        app = create_app(database, TrailProvider())
        async with app.router.lifespan_context(app):
            s = app.state.trails
            topic = s.chat.repo.save_topic(Topic("Contexto de teste"))
            conversation = s.chat.repo.save_conversation(Conversation(topic.id))
            trail = Trail(
                topic_id=topic.id,
                title="Trilha",
                objective="Aprender",
                prior_knowledge="",
                preferences="",
                prerequisites=[],
            )
            s.repo.commit([trail])
            units = []
            for i in range(6):
                module = Module(
                    trail_id=trail.id,
                    position=i,
                    plan=ModulePlan(
                        title=f"Módulo {i}",
                        objectives=["Objetivo"],
                        criteria=["Critério"],
                        estimated_minutes=20,
                        lesson_titles=["Aula"],
                    ),
                )
                unit = Unit(module_id=module.id, position=0, title=f"Unidade {i}")
                message = s.chat.repo.save_message(
                    Message(conversation.id, "assistant", "Conteúdo sintético")
                )
                version = ContentVersion(
                    unit_id=unit.id,
                    number=1,
                    message_id=message.id,
                    model_id="local:test",
                    plan_version=1,
                    context="{}",
                )
                summary = LearningSummary(
                    version_id=version.id,
                    content=GeneratedSummary(
                        concepts=["C" * 160] * 6,
                        conclusions=["D" * 160] * 6,
                        next_steps=["E" * 160] * 4,
                    ),
                    difficulties="F" * 1000,
                    objective_attempts=0,
                    matching_answers=0,
                )
                s.repo.commit([module, unit, version, summary])
                units.append(unit)
            first = json.loads(s.context(units[0].id))
            assert first["previous_summaries"] == []
            context = json.loads(s.context(units[-1].id))
            assert 0 < len(context["previous_summaries"]) <= 3
            assert (
                len(json.dumps(context["previous_summaries"], ensure_ascii=False))
                <= 4500
            )
            assert context["omitted_summaries"] == 5 - len(
                context["previous_summaries"]
            )

    asyncio.run(scenario())
