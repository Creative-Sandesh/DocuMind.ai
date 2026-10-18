"""Teacher role, ownership, assignment and real analytics workflow."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.documents import router as document_router
from app.api.learning_content import router as catalog_router
from app.api.learning_tools import router as learning_tools_router
from app.api.student import router as student_router
from app.api.teacher import router as teacher_router
from app.services import memory_service
from app.services.database import database
from app.schemas.learning_tools import LessonResponse


QUESTION = {"type": "multiple_choice", "question": "What repeats code?", "options": ["loop", "list", "string", "number"],
            "correct_answer": "loop", "explanation": "A loop repeats code.", "difficulty": "beginner"}


class TeacherTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_patch = patch.object(memory_service, "DB_PATH", Path(self.directory.name) / "learning.sqlite3")
        self.database_patch.start()
        self.code_patch = patch.dict("os.environ", {"TEACHER_REGISTRATION_CODE": "teacher-secret"})
        self.code_patch.start()
        app = FastAPI()
        app.include_router(student_router)
        app.include_router(teacher_router)
        app.include_router(catalog_router)
        app.include_router(learning_tools_router)
        app.include_router(document_router, prefix="/api/documents")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.code_patch.stop()
        self.database_patch.stop()
        self.directory.cleanup()

    def student(self, email="student@example.com"):
        result = self.client.post("/api/student/register", json={"email": email, "password": "goodpassword", "display_name": "Student"})
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    def teacher(self, email="teacher@example.com", code="teacher-secret"):
        result = self.client.post("/api/teacher/register", json={"email": email, "password": "goodpassword", "display_name": "Teacher", "teacher_code": code})
        return result

    @staticmethod
    def auth(account):
        return {"Authorization": f"Bearer {account['token']}"}

    def test_role_gate_and_teacher_signup_code(self):
        student = self.student()
        self.assertEqual(self.teacher("bad@example.com", "wrong").status_code, 403)
        with patch.dict("os.environ", {"TEACHER_REGISTRATION_CODE": ""}):
            self.assertEqual(self.teacher("disabled@example.com").status_code, 403)
        self.assertEqual(self.client.get("/api/teacher/courses").status_code, 401)
        self.assertEqual(self.client.get("/api/teacher/courses", headers=self.auth(student)).status_code, 403)
        created = self.teacher()
        self.assertEqual(created.status_code, 201, created.text)
        teacher = created.json()
        self.assertEqual(teacher["user"]["role"], "teacher")
        self.assertEqual(self.client.post("/api/student/login", json={"email": "teacher@example.com", "password": "goodpassword"}).status_code, 200)
        self.assertEqual(self.client.get("/api/student/dashboard", headers=self.auth(teacher)).status_code, 403)
        self.assertEqual(self.client.post("/api/student/logout", headers=self.auth(teacher)).status_code, 204)
        self.assertEqual(self.client.get("/api/teacher/courses", headers=self.auth(teacher)).status_code, 401)

    def test_course_content_material_and_ownership(self):
        teacher = self.teacher().json()
        other = self.teacher("other@example.com").json()
        student = self.student()
        course = self.client.post("/api/teacher/courses", headers=self.auth(teacher), json={"title": "Python", "description": "Basics"})
        self.assertEqual(course.status_code, 201, course.text)
        course_id, subject_id = course.json()["id"], course.json()["subject_id"]
        self.assertEqual(self.client.put(f"/api/teacher/courses/{course_id}", headers=self.auth(other), json={"title": "Hacked"}).status_code, 404)
        self.assertEqual(self.client.post("/api/learning/topics", json={"subject_id": subject_id, "title": "Untrusted"}).status_code, 403)
        self.assertEqual(self.client.get("/api/learning/subjects").json()["subjects"], [])
        self.assertEqual(self.client.get(f"/api/learning/topics?subject_id={subject_id}").status_code, 404)
        topic = self.client.post(f"/api/teacher/courses/{course_id}/topics", headers=self.auth(teacher), json={"title": "Loops"})
        self.assertEqual(topic.status_code, 201, topic.text)
        topic_id = topic.json()["id"]
        self.assertEqual(self.client.post("/api/learning/lessons", json={"topic_id": topic_id, "title": "Untrusted"}).status_code, 403)
        self.assertEqual(self.client.get(f"/api/learning/lessons?topic_id={topic_id}").status_code, 404)
        document_id = str(uuid4())
        with patch("app.api.teacher.process_document", new_callable=AsyncMock, return_value={"document_id": document_id, "filename": "notes.pdf"}):
            uploaded = self.client.post(f"/api/teacher/courses/{course_id}/materials", headers=self.auth(teacher), files={"file": ("notes.pdf", b"pdf", "application/pdf")})
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        material_id = uploaded.json()["id"]
        self.assertEqual(self.client.post("/api/learning/generate-lesson", json={"topic": "Loops", "document_ids": [document_id]}).status_code, 404)
        self.assertEqual(self.client.post("/api/student/learning/generate-lesson", headers=self.auth(student), json={"topic": "Loops", "document_ids": [document_id]}).status_code, 404)
        documents_path = Path(self.directory.name) / "documents"
        documents_path.mkdir()
        (documents_path / f"file{document_id}.marker.md").write_text("Parsed content", encoding="utf-8")
        (documents_path / f"file{document_id}.pdf").write_bytes(b"course material")
        with patch("app.api.student.DOCUMENT_DIR", documents_path), patch("app.api.teacher.DOCUMENT_DIR", documents_path):
            self.assertEqual(self.client.get(f"/api/student/courses/{course_id}/materials/{material_id}/download", headers=self.auth(student)).status_code, 404)
            self.assertEqual(self.client.get(f"/api/teacher/courses/{course_id}/materials/{material_id}/download", headers=self.auth(other)).status_code, 404)
            self.assertEqual(self.client.get(f"/api/teacher/courses/{course_id}/materials/{material_id}/download", headers=self.auth(teacher)).content, b"course material")
            self.client.post(f"/api/teacher/courses/{course_id}/students", headers=self.auth(teacher), json={"email": student["user"]["email"]})
            self.assertEqual(self.client.get(f"/api/student/courses/{course_id}/materials/{material_id}/download", headers=self.auth(student)).content, b"course material")
        generated_lesson = LessonResponse.model_validate({"lesson": {"title": "Loops", "introduction": "Intro", "sections": [{"heading": "One", "explanation": "First", "examples": ["Example"]}, {"heading": "Two", "explanation": "Second", "examples": ["Example"]}], "key_takeaways": ["One", "Two"], "practice_questions": ["Question"], "summary": "Summary"}, "difficulty": "beginner", "language": "english"})
        with patch("app.api.student.generate_lesson", new_callable=AsyncMock, return_value=generated_lesson):
            self.assertEqual(self.client.post("/api/student/learning/generate-lesson", headers=self.auth(student), json={"topic": "Loops", "document_ids": [document_id]}).status_code, 200)
        self.assertEqual(self.client.put(f"/api/teacher/courses/{course_id}/materials/{material_id}", headers=self.auth(other), json={"title": "Wrong"}).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/documents/{document_id}").status_code, 403)
        with patch("app.api.documents.list_documents", return_value=[{"document_id": document_id, "filename": "notes.pdf", "chunks": 1}]):
            self.assertEqual(self.client.get("/api/documents").json()["documents"], [])
        updated = self.client.put(f"/api/teacher/courses/{course_id}/materials/{material_id}", headers=self.auth(teacher), json={"title": "Chapter 1", "description": "Read first"})
        self.assertEqual(updated.json()["title"], "Chapter 1")
        lesson_body = {"topic_id": topic_id, "title": "For loops", "body": "A for loop repeats.", "objectives": ["Write a loop"], "source_document_ids": [document_id]}
        lesson = self.client.post(f"/api/teacher/courses/{course_id}/lessons", headers=self.auth(teacher), json=lesson_body)
        self.assertEqual(lesson.status_code, 201, lesson.text)
        self.assertEqual(self.client.get(f"/api/learning/lessons/{lesson.json()['id']}").status_code, 404)
        self.assertEqual(self.client.get(f"/api/student/lessons/{lesson.json()['id']}", headers=self.auth(student)).json()["body"], "A for loop repeats.")
        self.assertEqual(self.client.put(f"/api/teacher/courses/{course_id}/lessons/{lesson.json()['id']}", headers=self.auth(other), json=lesson_body).status_code, 404)
        with patch("app.api.teacher.delete_document_chunks", return_value=1), patch("app.api.teacher.delete_document_file"):
            self.assertEqual(self.client.delete(f"/api/teacher/courses/{course_id}/materials/{material_id}", headers=self.auth(teacher)).status_code, 204)
        self.assertEqual(self.client.get(f"/api/teacher/courses/{course_id}/materials", headers=self.auth(teacher)).json()["materials"], [])

    def test_assignment_grading_and_real_analytics(self):
        teacher = self.teacher().json()
        other = self.teacher("other@example.com").json()
        student = self.student()
        course = self.client.post("/api/teacher/courses", headers=self.auth(teacher), json={"title": "Python"}).json()
        course_id = course["id"]
        topic = self.client.post(f"/api/teacher/courses/{course_id}/topics", headers=self.auth(teacher), json={"title": "Loops"}).json()
        lesson = self.client.post(f"/api/teacher/courses/{course_id}/lessons", headers=self.auth(teacher), json={"topic_id": topic["id"], "title": "For loops"}).json()
        enrolled = self.client.post(f"/api/teacher/courses/{course_id}/students", headers=self.auth(teacher), json={"email": student["user"]["email"]})
        self.assertEqual(enrolled.status_code, 201)
        draft = self.client.post(f"/api/teacher/courses/{course_id}/quizzes", headers=self.auth(teacher), json={"topic_id": topic["id"], "quiz": {"title": "Loops quiz", "questions": [QUESTION]}})
        self.assertEqual(draft.status_code, 201, draft.text)
        quiz_id = draft.json()["id"]
        self.assertEqual(self.client.post(f"/api/teacher/quizzes/{quiz_id}/assign", headers=self.auth(teacher), json={}).status_code, 409)
        self.assertEqual(self.client.post(f"/api/teacher/quizzes/{quiz_id}/publish", headers=self.auth(other)).status_code, 404)
        self.assertEqual(self.client.post(f"/api/teacher/quizzes/{quiz_id}/publish", headers=self.auth(teacher)).status_code, 200)
        self.assertEqual(self.client.put(f"/api/teacher/quizzes/{quiz_id}", headers=self.auth(teacher), json={"quiz": {"title": "Changed", "questions": [QUESTION]}}).status_code, 409)
        self.assertEqual(self.client.post(f"/api/teacher/quizzes/{quiz_id}/assign", headers=self.auth(teacher), json={}).json()["assigned"], 1)
        assignment = self.client.get("/api/student/assignments", headers=self.auth(student)).json()["assignments"][0]
        self.assertNotIn("correct_answer", str(assignment))
        self.assertEqual(assignment["course_title"], "Python")
        practice_id = assignment["practice_quiz_id"]
        self.assertEqual(self.client.post(f"/api/student/quizzes/{practice_id}/attempts", headers=self.auth(student), json={"answers": [{"question_index": 0, "answer": "list"}]}).status_code, 201)
        self.assertEqual(self.client.post(f"/api/student/quizzes/{practice_id}/attempts", headers=self.auth(student), json={"answers": [{"question_index": 0, "answer": "loop"}]}).status_code, 409)
        second_quiz = self.client.post(f"/api/teacher/courses/{course_id}/quizzes", headers=self.auth(teacher), json={"topic_id": topic["id"], "quiz": {"title": "Loops quiz 2", "questions": [QUESTION]}}).json()
        self.client.post(f"/api/teacher/quizzes/{second_quiz['id']}/publish", headers=self.auth(teacher))
        self.client.post(f"/api/teacher/quizzes/{second_quiz['id']}/assign", headers=self.auth(teacher), json={})
        second_assignment = next(item for item in self.client.get("/api/student/assignments", headers=self.auth(student)).json()["assignments"] if item["title"] == "Loops quiz 2")
        self.assertEqual(self.client.post(f"/api/student/quizzes/{second_assignment['practice_quiz_id']}/attempts", headers=self.auth(student), json={"answers": [{"question_index": 0, "answer": "list"}]}).status_code, 201)
        self.assertEqual(self.client.put(f"/api/student/lessons/{lesson['id']}/complete", headers=self.auth(student)).status_code, 200)
        study = self.client.post("/api/student/study-sessions", headers=self.auth(student), json={"course_id": course_id}).json()
        with database() as db:
            db.execute("UPDATE study_sessions SET started_at = ? WHERE id = ?", ((datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat(), study["id"]))
        self.assertEqual(self.client.post(f"/api/student/study-sessions/{study['id']}/end", headers=self.auth(student)).status_code, 200)
        analytics = self.client.get(f"/api/teacher/courses/{course_id}/analytics", headers=self.auth(teacher))
        self.assertEqual(analytics.status_code, 200, analytics.text)
        self.assertEqual(analytics.json()["summary"]["students"], 1)
        self.assertEqual(analytics.json()["summary"]["completion_rate_percent"], 100.0)
        self.assertEqual(analytics.json()["summary"]["average_score_percent"], 0.0)
        self.assertGreaterEqual(analytics.json()["summary"]["study_seconds"], 89)
        self.assertEqual(analytics.json()["topics"][0]["topic"], "Loops")
        self.assertEqual(analytics.json()["weak_topic_distribution"], [{"topic": "Loops", "students": 1}])
        self.assertEqual(analytics.json()["students"][0]["lessons_completed"], 1)
        self.assertEqual(self.client.get(f"/api/teacher/courses/{course_id}/analytics", headers=self.auth(other)).status_code, 404)
        results = self.client.get(f"/api/teacher/quizzes/{quiz_id}/results", headers=self.auth(teacher)).json()["results"]
        self.assertEqual(results[0]["answers"][0]["submitted_answer"], "list")
        self.assertEqual(self.client.delete(f"/api/teacher/courses/{course_id}/students/{student['user']['id']}", headers=self.auth(teacher)).status_code, 204)
        self.assertEqual(self.client.get("/api/student/assignments", headers=self.auth(student)).json()["assignments"], [])
        self.assertEqual(self.client.get(f"/api/teacher/quizzes/{quiz_id}/results", headers=self.auth(teacher)).json()["results"], [])


if __name__ == "__main__":
    unittest.main()
