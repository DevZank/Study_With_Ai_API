import os
import sqlite3
from pathlib import Path

from sqlalchemy import Engine, create_engine, event

ROOT = Path(__file__).resolve().parents[4]


def database_path() -> Path:
    return Path(
        os.environ.get("STUDY_DB_PATH", str(ROOT / "data" / "study.sqlite3"))
    ).resolve()


def engine_for(path: Path) -> Engine:
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        "sqlite:///" + path.as_posix(),
        connect_args={"check_same_thread": False, "timeout": 5},
    )

    @event.listens_for(engine, "connect")
    def configure(connection: sqlite3.Connection, _: object) -> None:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")

    return engine
