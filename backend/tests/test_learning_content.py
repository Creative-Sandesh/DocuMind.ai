"""Version 2 learning catalog API and migration checks."""

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.learning_content import router
from app.services import memory_service


class LearningContentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "conversations.sqlite3"
        self.database_patch = patch.object(memory_service, "DB_PATH", self.database_path)
        self.database_patch.start()
        application = FastAPI()
        application.include_router(router)
        self.client = TestClient(application)

    def tearDown(self):
        self.client.close()
        self.database_patch.stop()
        self.directory.cleanup()

    def create_subject_and_topic(self):
        subject = self.client.post("/api/learning/subjects", json={"title": "Python"})
        self.assertEqual(subject.status_code, 201)
        topic = self.client.post(
            "/api/learning/topics",
            json={"subject_id": subject.json()["id"], "title": "Loops"},
        )
        self.assertEqual(topic.status_code, 201)
        return subject.json(), topic.json()

    def test_catalog_hierarchy_persists_and_reuses_conversation_database(self):
        conversation = memory_service.create_conversation(str(uuid4()))
        subject, topic = self.create_subject_and_topic()
        document_id = str(uuid4())
        with patch("app.api.learning_content.document_exists", return_value=True):
            lesson = self.client.post(
                "/api/learning/lessons",
                json={
                    "topic_id": topic["id"], "title": "For loops",
                    "difficulty": "beginner", "summary": "Repeat an action",
                    "objectives": ["Read a loop", "Write a loop"],
                    "source_document_ids": [document_id],
                },
            )
        self.assertEqual(lesson.status_code, 201)
        self.assertEqual(lesson.json()["objectives"], ["Read a loop", "Write a loop"])
        self.assertEqual(lesson.json()["source_document_ids"], [document_id])
        self.assertEqual(
            self.client.get(f"/api/learning/topics?subject_id={subject['id']}").json()["topics"][0]["id"],
            topic["id"],
        )
        self.assertEqual(
            self.client.get(f"/api/learning/lessons/{lesson.json()['id']}").json()["title"],
            "For loops",
        )
        self.assertEqual(
            len(self.client.get(f"/api/learning/lessons?topic_id={topic['id']}").json()["lessons"]), 1
        )
        self.assertIsNotNone(memory_service.get_conversation(conversation["conversation_id"]))
        with closing(sqlite3.connect(self.database_path)) as database:
            versions = database.execute("SELECT version FROM schema_migrations").fetchall()
        self.assertEqual(versions, [("0001_learning_content",), ("0002_student_system",),
                                    ("0003_teacher_system",), ("0004_spaced_repetition",)])
        self.assertEqual(len(self.client.get("/api/learning/subjects").json()["subjects"]), 1)

    def test_validation_conflicts_and_missing_parents(self):
        subject, topic = self.create_subject_and_topic()
        self.assertEqual(
            self.client.post("/api/learning/subjects", json={"title": "python"}).status_code, 409
        )
        self.assertEqual(
            self.client.post("/api/learning/subjects", json={"title": "   "}).status_code, 422
        )
        self.assertEqual(
            self.client.post("/api/learning/topics", json={
                "subject_id": str(uuid4()), "title": "Unknown"
            }).status_code, 404
        )
        self.assertEqual(
            self.client.post("/api/learning/topics", json={
                "subject_id": subject["id"], "title": "loops"
            }).status_code, 409
        )
        self.assertEqual(
            self.client.post("/api/learning/lessons", json={
                "topic_id": topic["id"], "title": "Bad", "difficulty": "expert"
            }).status_code, 422
        )
        self.assertEqual(
            self.client.post("/api/learning/lessons", json={
                "topic_id": topic["id"], "title": "Bad",
                "objectives": ["Same", "same"]
            }).status_code, 422
        )

    def test_document_links_require_an_existing_source(self):
        _, topic = self.create_subject_and_topic()
        with patch("app.api.learning_content.document_exists", return_value=False):
            response = self.client.post("/api/learning/lessons", json={
                "topic_id": topic["id"], "title": "Linked lesson",
                "source_document_ids": [str(uuid4())],
            })
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.client.get("/api/learning/lessons").json()["lessons"], [])


if __name__ == "__main__":
    unittest.main()
