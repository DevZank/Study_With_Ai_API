import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config

from alembic import command
from study_api.domain.chat import LOCAL_PROFILE_ID
from study_api.domain.content import PublicDocument
from study_api.domain.exercises import Exercise, Kind, grade


@pytest.mark.parametrize(
    "kind,key,response,score",
    [
        ("multiple_choice", "a", "a", 1),
        ("multiple_choice", "a", "b", 0),
        ("true_false", "true", "true", 1),
        ("true_false", "true", "false", 0),
        ("fill_blank", "Quatro", " quatro ", 1),
        ("fill_blank", "quatro", "cinco", 0),
        ("open", "Referência", "Resposta autoral", None),
    ],
)
def test_grade(kind: Kind, key: str, response: str, score: float | None) -> None:
    exercise = Exercise("message", kind, "Pergunta", "[]", key, "Explicação", "[]")
    result = grade(exercise, response, str(uuid4()))
    assert result.score == score
    assert result.response == response
    if kind == "open":
        assert "nenhuma nota automática" in result.feedback


def test_public_schema_has_no_answer_key() -> None:
    schema = json.dumps(PublicDocument.model_json_schema())
    assert "answer_key" not in schema
    assert "GeneratedExercise" not in schema


def test_upgrade_preserves_legacy_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "old.sqlite3"
    monkeypatch.setenv("STUDY_DB_PATH", str(path))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "0001")
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO topics(id,owner_id,title,status,created_at,updated_at) VALUES('t',?,'Legado','active','2026','2026')",
            (LOCAL_PROFILE_ID,),
        )
        connection.execute(
            "INSERT INTO conversations(id,owner_id,topic_id,title,created_at,updated_at) VALUES('c',?,'t','Conversa','2026','2026')",
            (LOCAL_PROFILE_ID,),
        )
        connection.execute(
            "INSERT INTO messages(id,owner_id,conversation_id,role,content,model_id,status,created_at,updated_at) VALUES('m',?,'c','assistant','Texto que deve permanecer','local','completed','2026','2026')",
            (LOCAL_PROFILE_ID,),
        )
    command.upgrade(config, "head")
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT content,response_format,document_json,mode FROM messages WHERE id='m'"
        ).fetchone() == ("Texto que deve permanecer", "text", "", "learn")
        assert connection.execute(
            "SELECT active_mode FROM conversations WHERE id='c'"
        ).fetchone() == ("learn",)
