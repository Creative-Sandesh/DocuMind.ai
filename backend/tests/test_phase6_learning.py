"""Phase 6 personalized practice, scheduled reviews, recommendations, and offline speech."""

import asyncio
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.student import router
from app.schemas.learning_tools import FlashcardResponse, QuizGenerateRequest, QuizResponse
from app.schemas.student import AttemptRequest
from app.services import memory_service, personalized_learning_service, speech_service, student_service
from app.services.database import database
from app.services.recommendation_service import _recommendations
from app.services.spaced_repetition_service import schedule
from app.services.learning_tools_service import generate_quiz


QUIZ = QuizResponse.model_validate({"quiz": {"title": "Loops", "questions": [{
    "type": "multiple_choice", "question": "What repeats code?", "options": ["loop", "list", "string", "number"],
    "correct_answer": "loop", "explanation": "A loop repeats code.", "difficulty": "beginner",
}]}})
CARDS = FlashcardResponse.model_validate({"flashcards": [{
    "front": "What is a loop?", "back": "A structure that repeats code.", "topic": "Loops",
    "difficulty": "beginner", "source_numbers": [],
}]})


class Phase6LearningTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(memory_service, "DB_PATH", Path(self.directory.name) / "learning.sqlite3")
        self.db_patch.start()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.db_patch.stop()
        self.directory.cleanup()

    def account(self, email):
        response = self.client.post("/api/student/register", json={
            "email": email, "password": "goodpassword", "display_name": "Learner",
        })
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    @staticmethod
    def headers(account):
        return {"Authorization": f"Bearer {account['token']}"}

    def mistake(self, student_id, topic="Loops"):
        quiz = student_service.save_quiz(student_id, topic, QUIZ)
        student_service.submit_attempt(student_id, quiz["quiz_id"], AttemptRequest.model_validate({
            "answers": [{"question_index": 0, "answer": "list"}],
        }))

    def test_personalized_quiz_uses_owned_weak_evidence_and_saved_errors(self):
        owner, other = self.account("owner@example.com"), self.account("other@example.com")
        for _ in range(5):
            self.mistake(owner["user"]["id"])
        plan = personalized_learning_service.personalized_plan(owner["user"]["id"])
        self.assertEqual(plan["status"], "weak")
        self.assertEqual(plan["difficulty"], "beginner")
        self.assertEqual(plan["prior_errors"], ["What repeats code?"])
        with patch("app.api.student.generate_quiz", new_callable=AsyncMock, return_value=QUIZ) as generated:
            response = self.client.post("/api/student/quizzes/personalized", headers=self.headers(owner), json={})
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["plan"]["topic_key"], "practice:loops")
            self.assertIn("What repeats code?", generated.call_args.kwargs["focus_context"])
        self.assertEqual(self.client.post("/api/student/quizzes/personalized", headers=self.headers(other),
                                          json={"topic_key": "practice:loops"}).status_code, 404)
        self.assertEqual(self.client.post("/api/student/quizzes/personalized", json={}).status_code, 401)

    def test_personalized_focus_reaches_structured_quiz_generation(self):
        with patch("app.services.learning_tools_service._source_context", new_callable=AsyncMock,
                   return_value=("", [])), patch("app.services.learning_tools_service._generate_json",
                   new_callable=AsyncMock, return_value=QUIZ.quiz.model_dump()) as generated:
            result = asyncio.run(generate_quiz(QuizGenerateRequest(topic="Loops", question_count=1),
                                               focus_context="Revisit the concept behind a missed loop question."))
        self.assertEqual(result.quiz.questions[0].question, "What repeats code?")
        self.assertIn("Revisit the concept behind a missed loop question", generated.call_args.args[1])

    def test_unpracticed_catalog_topic_requires_access_and_includes_objective(self):
        owner, other = self.account("owner@example.com"), self.account("other@example.com")
        subject_id, topic_id, lesson_id, course_id, teacher_id = (str(uuid4()) for _ in range(5))
        with database() as db:
            db.execute("INSERT INTO users VALUES (?, 'teacher@example.com', 'unused', 'teacher', 'now')", (teacher_id,))
            db.execute("INSERT INTO subjects VALUES (?, 'Science', '', 'now')", (subject_id,))
            db.execute("INSERT INTO topics VALUES (?, ?, 'Cells', '', 0, 'now')", (topic_id, subject_id))
            db.execute("INSERT INTO lessons VALUES (?, ?, 'Cell basics', '', '', 'beginner', 0, 'now', 'now')", (lesson_id, topic_id))
            db.execute("INSERT INTO lesson_objectives VALUES (?, 0, 'Identify the nucleus')", (lesson_id,))
            db.execute("INSERT INTO courses (id, title, description, created_at, teacher_id, subject_id) VALUES (?, 'Science course', '', 'now', ?, ?)",
                       (course_id, teacher_id, subject_id))
            db.execute("INSERT INTO course_enrollments VALUES (?, ?, 'now')", (course_id, owner["user"]["id"]))
        plan = personalized_learning_service.personalized_plan(owner["user"]["id"])
        self.assertEqual(plan["status"], "unpracticed")
        self.assertEqual(plan["topic_key"], f"catalog:{topic_id}")
        self.assertEqual(plan["lesson_objectives"], ["Identify the nucleus"])
        self.assertIsNone(personalized_learning_service.personalized_plan(other["user"]["id"]))
        self.assertEqual(self.client.post("/api/student/quizzes/personalized", headers=self.headers(other),
                                          json={"topic_key": f"catalog:{topic_id}"}).status_code, 404)
        with patch("app.api.student.generate_quiz", new_callable=AsyncMock, return_value=QUIZ):
            saved = self.client.post("/api/student/quizzes/personalized", headers=self.headers(owner),
                                     json={"topic_key": f"catalog:{topic_id}"})
        self.assertEqual(saved.status_code, 201, saved.text)
        attempt = self.client.post(f"/api/student/quizzes/{saved.json()['quiz_id']}/attempts",
                                   headers=self.headers(owner), json={"answers": [{"question_index": 0, "answer": "list"}]})
        self.assertEqual(attempt.status_code, 201, attempt.text)
        profile = self.client.get("/api/student/knowledge-profile", headers=self.headers(owner)).json()["topics"][0]
        self.assertEqual(profile["topic_key"], f"catalog:{topic_id}")
        self.assertEqual(personalized_learning_service.personalized_plan(owner["user"]["id"])["status"], "insufficient_evidence")

    def test_review_schedule_and_api_history_are_reproducible_and_owned(self):
        at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        first = schedule(0, 0, 2.5, "good", at)
        second = schedule(first["repetitions"], first["interval_days"], first["ease_factor"],
                          "good", datetime.fromisoformat(first["next_review_at"]))
        self.assertEqual(first["interval_days"], 1)
        self.assertEqual(second["interval_days"], 3)
        self.assertEqual(schedule(0, 0, 2.5, "easy", at)["interval_days"], 3)
        self.assertEqual(schedule(2, 3, 2.5, "hard", at)["ease_factor"], 2.35)
        self.assertEqual(schedule(2, 3, 2.5, "again", at)["next_review_at"],
                         "2026-01-01T00:10:00+00:00")

        owner, other = self.account("owner@example.com"), self.account("other@example.com")
        with patch("app.api.student._student_learning", new_callable=AsyncMock, return_value=CARDS):
            generated = self.client.post("/api/student/learning/generate-flashcards",
                                         headers=self.headers(owner), json={"topic": "Loops"})
        self.assertEqual(generated.status_code, 200, generated.text)
        card_id = generated.json()["card_ids"][0]
        self.assertEqual(self.client.get("/api/student/reviews/due", headers=self.headers(owner)).json()["summary"]["due_count"], 1)
        self.assertEqual(self.client.get("/api/student/reviews/due", headers=self.headers(other)).json()["cards"], [])
        self.assertEqual(self.client.post(f"/api/student/reviews/{card_id}", headers=self.headers(other),
                                          json={"rating": "good"}).status_code, 404)
        reviewed = self.client.post(f"/api/student/reviews/{card_id}", headers=self.headers(owner), json={"rating": "good"})
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["interval_days"], 1)
        self.assertEqual(self.client.get("/api/student/reviews/due", headers=self.headers(owner)).json()["summary"]["due_count"], 0)
        self.assertEqual(self.client.post(f"/api/student/reviews/{card_id}", headers=self.headers(owner),
                                          json={"rating": "good"}).status_code, 409)
        events = self.client.get(f"/api/student/reviews/{card_id}/history", headers=self.headers(owner)).json()["events"]
        self.assertEqual([event["rating"] for event in events], ["good"])
        self.assertEqual(self.client.get(f"/api/student/reviews/{card_id}/history", headers=self.headers(other)).status_code, 404)

    def test_recommendations_cover_due_cards_weak_topics_and_available_lessons(self):
        owner = self.account("owner@example.com")
        student_id = owner["user"]["id"]
        for _ in range(5):
            self.mistake(student_id)
        with patch("app.api.student._student_learning", new_callable=AsyncMock, return_value=CARDS):
            self.client.post("/api/student/learning/generate-flashcards", headers=self.headers(owner), json={"topic": "Loops"})
        subject_id, topic_id, lesson_id = (str(uuid4()) for _ in range(3))
        with database() as db:
            db.execute("INSERT INTO subjects VALUES (?, 'Science', '', 'now')", (subject_id,))
            db.execute("INSERT INTO topics VALUES (?, ?, 'Cells', '', 0, 'now')", (topic_id, subject_id))
            db.execute("INSERT INTO lessons VALUES (?, ?, 'Cell basics', '', '', 'beginner', 0, 'now', 'now')", (lesson_id, topic_id))
        items = self.client.get("/api/student/recommendations", headers=self.headers(owner)).json()["recommendations"]
        self.assertTrue({"review_flashcards", "practice_weak_topic", "next_lesson"}.issubset({item["type"] for item in items}))
        self.assertTrue(all(item["reason"] for item in items))
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.headers(owner)).json()["recommendations"], items)
        with database() as db:
            db.execute("INSERT INTO lesson_progress VALUES (?, ?, 'now')", (student_id, lesson_id))
            focused = _recommendations(db, student_id, [{"status": "weak", "topic_key": f"catalog:{topic_id}",
                "topic_id": topic_id, "topic": "Cells", "mastery_percent": 20, "status_reason": "Needs review"}])
        self.assertIn("revisit_lesson", {item["type"] for item in focused})

    def test_speech_reports_missing_local_models_without_network_fallback(self):
        account = self.account("owner@example.com")
        with patch.dict("os.environ", {"PIPER_MODEL_PATH": "", "VOSK_MODEL_PATH": ""}):
            status = self.client.get("/api/student/speech/status", headers=self.headers(account))
            self.assertEqual(status.status_code, 200)
            self.assertFalse(status.json()["text_to_speech"])
            self.assertTrue(status.json()["offline_only"])
            self.assertEqual(self.client.post("/api/student/speech/synthesize", headers=self.headers(account),
                                              json={"text": "Hello"}).status_code, 503)
            self.assertEqual(self.client.post("/api/student/speech/transcribe", headers=self.headers(account),
                                              files={"audio": ("voice.wav", b"invalid", "audio/wav")}).status_code, 503)
        with patch.object(speech_service, "status", return_value={"speech_to_text": True, "language": "en-US"}):
            self.assertRaises(speech_service.InvalidAudioError, speech_service.transcribe, b"invalid")

    def test_speech_synthesis_uses_only_configured_local_executable(self):
        def local_piper(args, **kwargs):
            Path(args[-1]).write_bytes(b"RIFF" + b"\x00" * 44)
            self.assertEqual(kwargs["input"], "Hello")
            self.assertNotIn("shell", kwargs)
            return SimpleNamespace(returncode=0)

        with patch.object(speech_service, "status", return_value={"text_to_speech": True}), \
             patch.dict("os.environ", {"PIPER_EXECUTABLE": "C:/local/piper.exe", "PIPER_MODEL_PATH": "C:/local/voice.onnx"}), \
             patch.object(speech_service.subprocess, "run", side_effect=local_piper) as invoked:
            self.assertTrue(speech_service.synthesize("Hello").startswith(b"RIFF"))
            self.assertEqual(invoked.call_args.args[0][:3],
                             ["C:/local/piper.exe", "--model", "C:/local/voice.onnx"])


if __name__ == "__main__":
    unittest.main()
