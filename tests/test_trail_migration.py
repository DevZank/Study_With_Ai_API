"""Valida atualização aditiva de um banco do Marco 2 com histórico existente."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect

from alembic import command
from study_api.infrastructure.db.database import engine_for
from study_api.infrastructure.db.repository import SqliteRepository


def test_upgrade_from_milestone2_keeps_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "previous.sqlite3"
    monkeypatch.setenv("STUDY_DB_PATH", str(path))
    config = Config("alembic.ini")
    command.upgrade(config, "0002")
    engine = engine_for(path)
    # O repositório atual requer origin; o banco antigo recebe dados pelo seu contrato SQL.
    from sqlalchemy import text

    with engine.begin() as connection:
        topic_id, conversation_id, message_id = (
            "old-topic",
            "old-conversation",
            "old-message",
        )
        connection.execute(
            text(
                "INSERT INTO topics (id,owner_id,created_at,updated_at,title,status) VALUES (:id,:owner,'old','old','Tema antigo','active')"
            ),
            {"id": topic_id, "owner": "00000000-0000-0000-0000-000000000001"},
        )
        connection.execute(
            text(
                "INSERT INTO conversations (id,owner_id,created_at,updated_at,topic_id,title,active_mode) VALUES (:id,:owner,'old','old',:topic,'Conversa antiga','learn')"
            ),
            {
                "id": conversation_id,
                "owner": "00000000-0000-0000-0000-000000000001",
                "topic": topic_id,
            },
        )
        connection.execute(
            text(
                "INSERT INTO messages (id,owner_id,created_at,updated_at,conversation_id,role,content,status,model_id,mode,response_format,document_json,notice) VALUES (:id,:owner,'old','old',:conversation,'assistant','Histórico preservado','completed','','learn','text','','')"
            ),
            {
                "id": message_id,
                "owner": "00000000-0000-0000-0000-000000000001",
                "conversation": conversation_id,
            },
        )
    engine.dispose()
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    engine = engine_for(path)
    repo = SqliteRepository(engine)
    assert repo.message(message_id).content == "Histórico preservado"
    assert repo.conversation(conversation_id).origin == "free"
    assert {
        "trails",
        "trail_modules",
        "lessons",
        "lesson_versions",
        "learning_summaries",
        "trail_jobs",
        "concepts",
        "concept_mastery",
        "flashcards",
        "review_states",
        "review_events",
        "xp_events",
        "achievements",
        "earned_achievements",
        "progress_preferences",
    } <= set(inspect(engine).get_table_names())
    engine.dispose()
