"""Student persistence and authorization regression checks."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.student import router
from app.schemas.learning_tools import QuizResponse
from app.services import memory_service, student_service
from app.services.database import database


QUIZ = QuizResponse.model_validate({"quiz": {"title": "Loops", "questions": [{
    "type": "multiple_choice", "question": "What repeats code?", "options": ["loop", "list", "string", "number"],
    "correct_answer": "loop", "explanation": "A loop repeats code.", "difficulty": "beginner",
}]}})


class StudentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.patch = patch.object(memory_service, "DB_PATH", Path(self.directory.name) / "learning.sqlite3")
        self.patch.start()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.patch.stop()
        self.directory.cleanup()

    def account(self, email):
        response = self.client.post("/api/student/register", json={"email": email, "password": "goodpassword", "display_name": "Learner"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    @staticmethod
    def headers(account):
        return {"Authorization": f"Bearer {account['token']}"}

    def test_accounts_profiles_and_revocation(self):
        first = self.account("first@example.com")
        self.assertEqual(self.client.post("/api/student/register", json={"email": "FIRST@example.com", "password": "goodpassword", "display_name": "Other"}).status_code, 409)
        self.assertEqual(self.client.post("/api/student/login", json={"email": "first@example.com", "password": "wrong"}).status_code, 401)
        self.assertEqual(self.client.get("/api/student/me").status_code, 401)
        self.assertEqual(self.client.get("/api/student/me", headers=self.headers(first)).json()["email"], "first@example.com")
        updated = self.client.put("/api/student/profile", headers=self.headers(first), json={"display_name": "Student One", "preferred_language": "nepali", "learning_goals": "Learn loops"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["learning_goals"], "Learn loops")
        self.assertEqual(self.client.post("/api/student/logout", headers=self.headers(first)).status_code, 204)
        self.assertEqual(self.client.get("/api/student/me", headers=self.headers(first)).status_code, 401)
        self.assertEqual(self.client.post("/api/student/login", json={"email": "first@example.com", "password": "goodpassword"}).status_code, 200)
        with database() as db:
            password_hash = db.execute("SELECT password_hash FROM users WHERE email = ?", ("first@example.com",)).fetchone()[0]
        self.assertNotIn("goodpassword", password_hash)
        fresh = self.client.post("/api/student/login", json={"email": "first@example.com", "password": "goodpassword"}).json()
        with database() as db:
            db.execute("UPDATE auth_sessions SET expires_at = '2000-01-01T00:00:00+00:00' WHERE user_id = ?", (first["user"]["id"],))
        self.assertEqual(self.client.get("/api/student/me", headers=self.headers(fresh)).status_code, 401)

    def test_owned_quiz_attempt_and_dashboard(self):
        first, second = self.account("first@example.com"), self.account("second@example.com")
        with patch("app.api.student.generate_quiz", new_callable=AsyncMock, return_value=QUIZ):
            generated = self.client.post("/api/student/quizzes/generate", headers=self.headers(first), json={"topic": "Python loops"})
        self.assertEqual(generated.status_code, 201, generated.text)
        quiz_id = generated.json()["quiz_id"]
        submission = {"answers": [{"question_index": 0, "answer": "loop"}]}
        self.assertEqual(self.client.post(f"/api/student/quizzes/{quiz_id}/attempts", headers=self.headers(second), json=submission).status_code, 404)
        attempt = self.client.post(f"/api/student/quizzes/{quiz_id}/attempts", headers=self.headers(first), json=submission)
        self.assertEqual(attempt.status_code, 201, attempt.text)
        self.assertEqual(attempt.json()["evaluation"]["score"], 1)
        attempt_id = attempt.json()["id"]
        self.assertEqual(self.client.get(f"/api/student/attempts/{attempt_id}", headers=self.headers(second)).status_code, 404)
        self.assertEqual(self.client.get(f"/api/student/attempts/{attempt_id}", headers=self.headers(first)).json()["answers"][0]["submitted_answer"], "loop")
        self.assertEqual(len(self.client.get("/api/student/attempts", headers=self.headers(first)).json()["attempts"]), 1)
        self.assertEqual(self.client.get("/api/student/attempts", headers=self.headers(second)).json()["attempts"], [])
        self.assertEqual(self.client.post(f"/api/student/quizzes/{quiz_id}/attempts", headers=self.headers(first), json={"answers": []}).status_code, 422)
        first_dashboard = self.client.get("/api/student/dashboard", headers=self.headers(first)).json()
        second_dashboard = self.client.get("/api/student/dashboard", headers=self.headers(second)).json()
        self.assertEqual(first_dashboard["total_attempts"], 1)
        self.assertEqual(first_dashboard["topic_progress"][0]["score"], 1)
        self.assertEqual(second_dashboard["total_attempts"], 0)
        self.assertEqual(first_dashboard["courses"], [])
        self.assertEqual(first_dashboard["recommendations"][0]["type"], "attempt_quiz")
        self.assertEqual(second_dashboard["recommendations"], [])

    def test_lesson_and_server_measured_study_duration(self):
        first, second = self.account("first@example.com"), self.account("second@example.com")
        subject_id, topic_id, lesson_id = str(uuid4()), str(uuid4()), str(uuid4())
        course_id = str(uuid4())
        with database() as db:
            db.execute("INSERT INTO courses (id, title, description, created_at) VALUES (?, 'Programming', 'Intro course', 'now')", (course_id,))
            db.execute("INSERT INTO course_enrollments VALUES (?, ?, 'now')", (course_id, first["user"]["id"]))
            db.execute("INSERT INTO subjects VALUES (?, 'Python', '', 'now')", (subject_id,))
            db.execute("INSERT INTO topics VALUES (?, ?, 'Loops', '', 0, 'now')", (topic_id, subject_id))
            db.execute("INSERT INTO lessons VALUES (?, ?, 'For loops', '', '', 'beginner', 0, 'now', 'now')", (lesson_id, topic_id))
        path = f"/api/student/lessons/{lesson_id}/complete"
        self.assertEqual(self.client.put(path, headers=self.headers(first)).status_code, 200)
        self.assertEqual(self.client.put(path, headers=self.headers(first)).status_code, 200)
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(first)).json()["lessons_completed"][0]["title"], "For loops")
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(first)).json()["courses"][0]["title"], "Programming")
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(second)).json()["lessons_completed"], [])
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(second)).json()["courses"], [])
        started = self.client.post("/api/student/study-sessions", headers=self.headers(first)).json()
        self.assertEqual(self.client.post("/api/student/study-sessions", headers=self.headers(first)).json()["id"], started["id"])
        self.assertEqual(self.client.post(f"/api/student/study-sessions/{started['id']}/end", headers=self.headers(second)).status_code, 404)
        with database() as db:
            db.execute("UPDATE study_sessions SET started_at = ? WHERE id = ?", ((datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat(), started["id"]))
        ended = self.client.post(f"/api/student/study-sessions/{started['id']}/end", headers=self.headers(first))
        self.assertEqual(ended.status_code, 200)
        self.assertGreaterEqual(ended.json()["duration_seconds"], 89)
        self.assertGreaterEqual(self.client.get("/api/student/dashboard", headers=self.headers(first)).json()["total_study_seconds"], 89)
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(second)).json()["total_study_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
