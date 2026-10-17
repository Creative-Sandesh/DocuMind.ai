"""SQLite-backed conversation sessions for the existing memory chat route."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4


MAX_HISTORY_MESSAGES = 12
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "conversations.sqlite3"


@contextmanager
def _database() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                document_ids_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL REFERENCES conversations(id)
                    ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sources_json TEXT
            );
            CREATE INDEX IF NOT EXISTS messages_conversation_id
                ON messages(conversation_id, id);
            """
        )
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(messages)")
        }
        if "sources_json" not in columns:
            connection.execute("ALTER TABLE messages ADD COLUMN sources_json TEXT")
        conversation_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(conversations)")
        }
        if "document_ids_json" not in conversation_columns:
            connection.execute("ALTER TABLE conversations ADD COLUMN document_ids_json TEXT")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _document_ids(row: sqlite3.Row) -> list[str]:
    return json.loads(row["document_ids_json"]) if row["document_ids_json"] else [row["document_id"]]


def create_conversation(document_id: str, document_ids: list[str] | None = None) -> dict:
    selected_ids = document_ids or [document_id]
    if selected_ids[0] != document_id:
        raise ValueError("First selected document must match document_id")
    conversation_id = uuid4()
    now = datetime.now(timezone.utc).isoformat()
    with _database() as database:
        database.execute(
            "INSERT INTO conversations "
            "(id, document_id, document_ids_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(conversation_id), document_id, json.dumps(selected_ids), now, now),
        )
    return {
        "conversation_id": conversation_id,
        "document_id": document_id,
        "document_ids": selected_ids,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }


def get_conversation(conversation_id: UUID) -> dict | None:
    with _database() as database:
        row = database.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (str(conversation_id),),
        ).fetchone()
        if row is None:
            return None
        messages = database.execute(
            "SELECT role, content, created_at, sources_json FROM messages "
            "WHERE conversation_id = ? ORDER BY id",
            (str(conversation_id),),
        ).fetchall()
    return {
        "conversation_id": conversation_id,
        "document_id": row["document_id"],
        "document_ids": _document_ids(row),
        "title": next((message["content"] for message in messages if message["role"] == "user"), None),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "messages": [
            {
                "role": message["role"],
                "content": message["content"],
                "created_at": message["created_at"],
                "sources": json.loads(message["sources_json"])
                if message["sources_json"] else [],
            }
            for message in messages
        ],
    }


def list_conversations(document_id: str | None = None) -> list[dict]:
    query = "SELECT * FROM conversations ORDER BY updated_at DESC, id DESC"
    with _database() as database:
        rows = database.execute(query).fetchall()
        titles = {
            row["conversation_id"]: row["content"]
            for row in database.execute(
                "SELECT conversation_id, content FROM messages "
                "WHERE role = 'user' AND id IN ("
                "SELECT MIN(id) FROM messages WHERE role = 'user' GROUP BY conversation_id)"
            ).fetchall()
        }
    return [
        {
            "conversation_id": UUID(row["id"]),
            "document_id": row["document_id"],
            "document_ids": _document_ids(row),
            "title": titles.get(row["id"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
        if document_id is None or document_id in _document_ids(row)
    ]


def delete_conversation(conversation_id: UUID) -> bool:
    with _database() as database:
        deleted = database.execute(
            "DELETE FROM conversations WHERE id = ?",
            (str(conversation_id),),
        ).rowcount
    return deleted > 0


def get_or_create_conversation(
    document_id: str,
    conversation_id: UUID | None = None,
    document_ids: list[str] | None = None,
) -> tuple[UUID, list[dict[str, str]]]:
    selected_ids = document_ids or [document_id]
    if conversation_id is None:
        conversation_id = create_conversation(document_id, selected_ids)["conversation_id"]

    with _database() as database:
        row = database.execute(
            "SELECT document_id, document_ids_json FROM conversations WHERE id = ?",
            (str(conversation_id),),
        ).fetchone()
        if row is None:
            raise ValueError("Conversation not found")
        if set(_document_ids(row)) != set(selected_ids):
            raise ValueError("Conversation belongs to another document selection")
        messages = database.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (str(conversation_id), MAX_HISTORY_MESSAGES),
        ).fetchall()
    return conversation_id, [dict(message) for message in reversed(messages)]


def save_conversation_turn(
    conversation_id: UUID,
    user_message: str,
    assistant_message: str,
    sources: list[dict] | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _database() as database:
        exists = database.execute(
            "SELECT 1 FROM conversations WHERE id = ?",
            (str(conversation_id),),
        ).fetchone()
        if exists is None:
            raise ValueError("Conversation not found")
        database.executemany(
            "INSERT INTO messages "
            "(conversation_id, role, content, created_at, sources_json) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (str(conversation_id), "user", user_message, now, None),
                (
                    str(conversation_id), "assistant", assistant_message, now,
                    json.dumps(sources or []),
                ),
            ],
        )
        database.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, str(conversation_id)),
        )
