"""Phase 6.1 knowledge profiles use only a student's saved assessment evidence."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.student import router
from app.schemas.learning_tools import QuizResponse
from app.schemas.student import AttemptRequest
from app.services import memory_service, student_service
from app.services.adaptive_learning_service import assess_topic, recommend_difficulty
from app.services.database import database


MCQ = QuizResponse.model_validate({"quiz": {"title": "Loops", "questions": [{
    "type": "multiple_choice", "question": "What repeats code?", "options": ["loop", "list", "string", "number"],
    "correct_answer": "loop", "explanation": "A loop repeats code.", "difficulty": "beginner",
}]}})
SHORT = QuizResponse.model_validate({"quiz": {"title": "Loops", "questions": [{
    "type": "short_answer", "question": "Explain a loop", "options": [], "correct_answer": "A loop repeats code",
    "explanation": "A loop repeats code.", "difficulty": "beginner", "rubric_keywords": ["loop", "repeats"],
}]}})


class KnowledgeProfileTests(unittest.TestCase):
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
        result = self.client.post("/api/student/register", json={
            "email": email, "password": "goodpassword", "display_name": "Learner",
        })
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    @staticmethod
    def headers(account):
        return {"Authorization": f"Bearer {account['token']}"}

    def attempt(self, student_id, topic, answer, response=MCQ):
        quiz = student_service.save_quiz(student_id, topic, response)
        result = student_service.submit_attempt(student_id, quiz["quiz_id"], AttemptRequest.model_validate({
            "answers": [{"question_index": 0, "answer": answer}],
        }))
        return result["id"]

    def test_profile_calculation_provisional_answers_and_ownership(self):
        first, second = self.account("first@example.com"), self.account("second@example.com")
        first_id = first["user"]["id"]
        self.assertEqual(self.client.get("/api/student/knowledge-profile").status_code, 401)
        self.assertEqual(self.client.get("/api/student/knowledge-profile", headers=self.headers(second)).json()["topics"], [])

        attempts = [
            self.attempt(first_id, "Python Loops", "list"),
            self.attempt(first_id, "python   loops", "loop"),
            self.attempt(first_id, "Python Loops", "loop"),
            self.attempt(first_id, "Python Loops", "loop"),
            self.attempt(first_id, "Python Loops", "loop", SHORT),
            self.attempt(first_id, "Python Loops", "loop"),
        ]
        with database() as db:
            for index, attempt_id in enumerate(attempts):
                db.execute("UPDATE quiz_attempts SET created_at = ? WHERE id = ?",
                           (f"2026-01-0{index + 1}T00:00:00+00:00", attempt_id))

        response = self.client.get("/api/student/knowledge-profile", headers=self.headers(first))
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["recent_window"], 3)
        self.assertEqual(len(payload["topics"]), 1)
        profile = payload["topics"][0]
        self.assertEqual(profile["topic_key"], "practice:python loops")
        self.assertEqual(profile["attempts"], 6)
        self.assertEqual(profile["correct_answers"], 4)
        self.assertEqual(profile["incorrect_answers"], 1)
        self.assertEqual(profile["provisional_answers"], 1)
        self.assertEqual(profile["recent_accuracy_percent"], 100)
        self.assertEqual(profile["mastery_percent"], 92)
        self.assertEqual(profile["evidence"], "supported")
        self.assertEqual(profile["last_practiced_at"], "2026-01-06T00:00:00Z")
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(first)).json()["knowledge_profile"], payload)
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(second)).json()["knowledge_profile"]["topics"], [])

    def test_provisional_only_topic_has_no_mastery(self):
        account = self.account("student@example.com")
        self.attempt(account["user"]["id"], "Writing", "An answer", SHORT)
        profile = self.client.get("/api/student/knowledge-profile", headers=self.headers(account)).json()["topics"][0]
        self.assertIsNone(profile["mastery_percent"])
        self.assertIsNone(profile["recent_accuracy_percent"])
        self.assertEqual(profile["provisional_answers"], 1)
        self.assertEqual(profile["evidence"], "early")
        self.assertEqual(profile["status"], "insufficient_evidence")

    def test_weak_and_strong_topics_are_evidence_gated_and_student_scoped(self):
        owner, other = self.account("owner@example.com"), self.account("other@example.com")
        student_id = owner["user"]["id"]
        self.attempt(student_id, "Algebra", "list")
        early = self.client.get("/api/student/knowledge-profile", headers=self.headers(owner)).json()["topics"][0]
        self.assertEqual(early["status"], "insufficient_evidence")
        for _ in range(4):
            self.attempt(student_id, "Algebra", "list")
            self.attempt(student_id, "Geometry", "loop")
        self.attempt(student_id, "Geometry", "loop")
        profiles = self.client.get("/api/student/knowledge-profile", headers=self.headers(owner)).json()["topics"]
        by_name = {profile["topic"]: profile for profile in profiles}
        self.assertEqual(by_name["Algebra"]["status"], "weak")
        self.assertEqual(by_name["Algebra"]["recommended_difficulty"], "beginner")
        self.assertEqual(by_name["Geometry"]["status"], "strong")
        self.assertEqual(by_name["Geometry"]["recommended_difficulty"], "advanced")
        self.assertEqual(self.client.get("/api/student/knowledge-profile", headers=self.headers(other)).json()["topics"], [])

    def test_adaptive_generation_uses_own_topic_evidence_and_is_optional(self):
        owner, other = self.account("owner@example.com"), self.account("other@example.com")
        for _ in range(5):
            self.attempt(owner["user"]["id"], "Algebra", "list")
        body = {"topic": "  algebra ", "difficulty": "intermediate", "question_count": 1,
                "question_types": ["multiple_choice"], "adaptive": True}
        with patch("app.api.student._generate", new_callable=AsyncMock, return_value=MCQ) as generated:
            response = self.client.post("/api/student/quizzes/generate", headers=self.headers(owner), json=body)
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["adaptive_decision"]["effective_difficulty"], "beginner")
            self.assertEqual(generated.call_args.args[1].difficulty, "beginner")
            other_response = self.client.post("/api/student/quizzes/generate", headers=self.headers(other), json=body)
            self.assertEqual(other_response.status_code, 201, other_response.text)
            self.assertEqual(other_response.json()["adaptive_decision"]["topic_status"], "insufficient_evidence")
            self.assertEqual(generated.call_args.args[1].difficulty, "intermediate")
            manual = self.client.post("/api/student/quizzes/generate", headers=self.headers(owner), json={**body, "adaptive": False})
            self.assertEqual(manual.status_code, 201, manual.text)
            self.assertIsNone(manual.json()["adaptive_decision"])
            self.assertEqual(generated.call_args.args[1].difficulty, "intermediate")

    def test_mixed_performance_keeps_level_and_recent_drop_can_flag_weak(self):
        mixed = {"evidence": "supported", "mastery_percent": 67, "recent_accuracy_percent": 65,
                 "incorrect_answers": 3}
        self.assertEqual(assess_topic(mixed)["status"], "developing")
        self.assertEqual(recommend_difficulty("developing", "advanced")["effective_difficulty"], "advanced")
        declining = {**mixed, "mastery_percent": 65, "recent_accuracy_percent": 40}
        self.assertEqual(assess_topic(declining)["status"], "weak")
        self.assertEqual(recommend_difficulty("weak", "beginner")["effective_difficulty"], "beginner")
        self.assertEqual(recommend_difficulty("strong", "advanced")["effective_difficulty"], "advanced")

    def test_catalog_topic_ids_keep_similar_topic_names_separate(self):
        account = self.account("student@example.com")
        student_id = account["user"]["id"]
        with database() as db:
            teacher_id = str(uuid4())
            db.execute("INSERT INTO users VALUES (?, 'teacher@example.com', 'unused', 'teacher', 'now')", (teacher_id,))
            for subject_title in ("Science", "History"):
                subject_id, topic_id, course_id, teacher_quiz_id, quiz_id, attempt_id = (str(uuid4()) for _ in range(6))
                db.execute("INSERT INTO subjects VALUES (?, ?, '', 'now')", (subject_id, subject_title))
                db.execute("INSERT INTO topics VALUES (?, ?, 'Introduction', '', 0, 'now')", (topic_id, subject_id))
                db.execute("INSERT INTO courses (id, title, description, created_at, teacher_id, subject_id) VALUES (?, ?, '', 'now', ?, ?)",
                           (course_id, subject_title, teacher_id, subject_id))
                db.execute("INSERT INTO teacher_quizzes VALUES (?, ?, ?, '{}', 'published', 'now', 'now', 'now')",
                           (teacher_quiz_id, course_id, topic_id))
                db.execute("INSERT INTO practice_quizzes (id, student_id, topic, quiz_json, created_at, teacher_quiz_id) VALUES (?, ?, 'Introduction', '{}', 'now', ?)",
                           (quiz_id, student_id, teacher_quiz_id))
                db.execute("INSERT INTO quiz_attempts VALUES (?, ?, ?, 1, 1, '2026-01-01T00:00:00+00:00')",
                           (attempt_id, quiz_id, student_id))
                db.execute("INSERT INTO attempt_answers VALUES (?, 0, 'right', 1, 1, 0)", (attempt_id,))
        profiles = self.client.get("/api/student/knowledge-profile", headers=self.headers(account)).json()["topics"]
        self.assertEqual(len(profiles), 2)
        self.assertEqual(len({profile["topic_key"] for profile in profiles}), 2)
        self.assertTrue(all(profile["topic_id"] for profile in profiles))


if __name__ == "__main__":
    unittest.main()
