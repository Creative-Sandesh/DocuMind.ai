"""SQLite learning catalog; shares the existing conversation database file."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from uuid import UUID, uuid4

from app.schemas.learning_content import LessonCreate, SubjectCreate, TopicCreate
from app.services import memory_service


MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"


class CatalogNotFoundError(Exception):
    pass


class CatalogConflictError(Exception):
    pass


@contextmanager
def _database() -> Iterator[sqlite3.Connection]:
    """Apply pending migrations before a catalog operation, preserving old data."""
    path = memory_service.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(path, timeout=10)
    database.row_factory = sqlite3.Row
    database.execute("PRAGMA foreign_keys = ON")
    try:
        database.execute("BEGIN IMMEDIATE")
        database.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        applied = {
            row["version"]
            for row in database.execute("SELECT version FROM schema_migrations")
        }
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration.stem in applied:
                continue
            # Migration files contain only SQL statements, with no procedural blocks.
            for statement in migration.read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    database.execute(statement)
            database.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (migration.stem, datetime.now(timezone.utc).isoformat()),
            )
        database.commit()
        yield database
        database.commit()
    except BaseException:
        database.rollback()
        raise
    finally:
        database.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lesson(database: sqlite3.Connection, row: sqlite3.Row) -> dict:
    lesson_id = row["id"]
    objectives = [
        item["objective"] for item in database.execute(
            "SELECT objective FROM lesson_objectives WHERE lesson_id = ? ORDER BY position",
            (lesson_id,),
        )
    ]
    document_ids = [
        item["document_id"] for item in database.execute(
            "SELECT document_id FROM lesson_documents WHERE lesson_id = ? ORDER BY rowid",
            (lesson_id,),
        )
    ]
    return {**dict(row), "objectives": objectives, "source_document_ids": document_ids}


def create_subject(request: SubjectCreate) -> dict:
    subject = {
        "id": str(uuid4()), "title": request.title,
        "description": request.description, "created_at": _now(),
    }
    with _database() as database:
        try:
            database.execute(
                "INSERT INTO subjects (id, title, description, created_at) VALUES (?, ?, ?, ?)",
                tuple(subject.values()),
            )
        except sqlite3.IntegrityError as error:
            raise CatalogConflictError("A subject with this title already exists") from error
    return subject


def list_subjects() -> list[dict]:
    with _database() as database:
        return [dict(row) for row in database.execute("SELECT * FROM subjects ORDER BY title")]


def create_topic(request: TopicCreate) -> dict:
    topic = {
        "id": str(uuid4()), "subject_id": str(request.subject_id),
        "title": request.title, "description": request.description,
        "position": request.position, "created_at": _now(),
    }
    with _database() as database:
        if not database.execute("SELECT 1 FROM subjects WHERE id = ?", (topic["subject_id"],)).fetchone():
            raise CatalogNotFoundError("Subject not found")
        try:
            database.execute(
                "INSERT INTO topics (id, subject_id, title, description, position, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)", tuple(topic.values()),
            )
        except sqlite3.IntegrityError as error:
            raise CatalogConflictError("A topic with this title already exists in the subject") from error
    return topic


def list_topics(subject_id: UUID | None = None) -> list[dict]:
    with _database() as database:
        if subject_id is not None and not database.execute(
            "SELECT 1 FROM subjects WHERE id = ?", (str(subject_id),)
        ).fetchone():
            raise CatalogNotFoundError("Subject not found")
        query = "SELECT * FROM topics"
        parameters: tuple[str, ...] = ()
        if subject_id is not None:
            query += " WHERE subject_id = ?"
            parameters = (str(subject_id),)
        return [dict(row) for row in database.execute(query + " ORDER BY position, title", parameters)]


def create_lesson(request: LessonCreate) -> dict:
    lesson = {
        "id": str(uuid4()), "topic_id": str(request.topic_id),
        "title": request.title, "summary": request.summary, "body": request.body,
        "difficulty": request.difficulty, "position": request.position,
        "created_at": _now(), "updated_at": _now(),
    }
    with _database() as database:
        if not database.execute("SELECT 1 FROM topics WHERE id = ?", (lesson["topic_id"],)).fetchone():
            raise CatalogNotFoundError("Topic not found")
        try:
            database.execute(
                "INSERT INTO lessons (id, topic_id, title, summary, body, difficulty, "
                "position, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(lesson.values()),
            )
        except sqlite3.IntegrityError as error:
            raise CatalogConflictError("A lesson with this title already exists in the topic") from error
        database.executemany(
            "INSERT INTO lesson_objectives (lesson_id, position, objective) VALUES (?, ?, ?)",
            [(lesson["id"], position, objective) for position, objective in enumerate(request.objectives)],
        )
        database.executemany(
            "INSERT INTO lesson_documents (lesson_id, document_id) VALUES (?, ?)",
            [(lesson["id"], str(document_id)) for document_id in request.source_document_ids],
        )
    return {
        **lesson, "objectives": request.objectives,
        "source_document_ids": [str(value) for value in request.source_document_ids],
    }


def get_lesson(lesson_id: UUID) -> dict:
    with _database() as database:
        row = database.execute("SELECT * FROM lessons WHERE id = ?", (str(lesson_id),)).fetchone()
        if row is None:
            raise CatalogNotFoundError("Lesson not found")
        return _lesson(database, row)


def list_lessons(topic_id: UUID | None = None) -> list[dict]:
    with _database() as database:
        if topic_id is not None and not database.execute(
            "SELECT 1 FROM topics WHERE id = ?", (str(topic_id),)
        ).fetchone():
            raise CatalogNotFoundError("Topic not found")
        query = "SELECT * FROM lessons"
        parameters: tuple[str, ...] = ()
        if topic_id is not None:
            query += " WHERE topic_id = ?"
            parameters = (str(topic_id),)
        return [
            _lesson(database, row)
            for row in database.execute(query + " ORDER BY position, title", parameters).fetchall()
        ]
