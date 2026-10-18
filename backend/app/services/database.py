"""Shared SQLite connection and additive migrations."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from app.services import memory_service


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    path = memory_service.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        applied = {row["version"] for row in connection.execute("SELECT version FROM schema_migrations")}
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration.stem in applied:
                continue
            for statement in migration.read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES (?, ?)", (migration.stem, datetime.now(timezone.utc).isoformat()))
        connection.commit()
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()
