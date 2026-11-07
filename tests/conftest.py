from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("STUDY_DB_PATH", str(path))
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    return path
