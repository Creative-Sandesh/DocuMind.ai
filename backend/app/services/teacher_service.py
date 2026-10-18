"""Teacher-owned course, material, enrollment and quiz records."""

import sqlite3
from contextlib import closing
from uuid import uuid4

from app.schemas.learning_tools import QuizResponse
from app.schemas.teacher import CourseInput, CourseLessonInput, CourseTopicInput, TeacherQuizInput
from app.services.auth_service import now
from app.services.database import database
from app.services.learning_content_service import _lesson


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def _course(db, teacher_id: str, course_id: str):
    row = db.execute("SELECT * FROM courses WHERE id = ? AND teacher_id = ?", (course_id, teacher_id)).fetchone()
    if not row:
        raise NotFound("Course not found")
    return row


def owned_course(teacher_id: str, course_id: str) -> dict:
    with database() as db:
        return dict(_course(db, teacher_id, course_id))


def list_courses(teacher_id: str) -> list[dict]:
    with database() as db:
        return [dict(row) for row in db.execute(
            "SELECT c.*, (SELECT COUNT(*) FROM course_enrollments e WHERE e.course_id = c.id) AS student_count "
            "FROM courses c WHERE c.teacher_id = ? ORDER BY c.title", (teacher_id,))]


def create_course(teacher_id: str, request: CourseInput) -> dict:
    course_id, subject_id, created = str(uuid4()), str(uuid4()), now()
    with database() as db:
        db.execute("INSERT INTO subjects VALUES (?, ?, ?, ?)",
                   (subject_id, f"{request.title[:145]} [{course_id[:8]}]", request.description, created))
        db.execute("INSERT INTO courses (id, title, description, created_at, teacher_id, subject_id) VALUES (?, ?, ?, ?, ?, ?)",
                   (course_id, request.title, request.description, created, teacher_id, subject_id))
        return dict(_course(db, teacher_id, course_id))


def update_course(teacher_id: str, course_id: str, request: CourseInput) -> dict:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        db.execute("UPDATE courses SET title = ?, description = ? WHERE id = ?", (request.title, request.description, course_id))
        if course["subject_id"]:
            db.execute("UPDATE subjects SET title = ?, description = ? WHERE id = ?",
                       (f"{request.title[:145]} [{course_id[:8]}]", request.description, course["subject_id"]))
        return dict(_course(db, teacher_id, course_id))


def list_topics(teacher_id: str, course_id: str) -> list[dict]:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        return [dict(row) for row in db.execute("SELECT * FROM topics WHERE subject_id = ? ORDER BY position, title", (course["subject_id"],))]


def create_topic(teacher_id: str, course_id: str, request: CourseTopicInput) -> dict:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        topic_id = str(uuid4())
        try:
            db.execute("INSERT INTO topics VALUES (?, ?, ?, ?, ?, ?)",
                       (topic_id, course["subject_id"], request.title, request.description, request.position, now()))
        except sqlite3.IntegrityError as error:
            raise Conflict("A topic with this title already exists") from error
        return dict(db.execute("SELECT * FROM topics WHERE id = ?", (topic_id,)).fetchone())


def _course_topic(db, course, topic_id: str):
    topic = db.execute("SELECT * FROM topics WHERE id = ? AND subject_id = ?", (topic_id, course["subject_id"])).fetchone()
    if not topic:
        raise NotFound("Topic not found in this course")
    return topic


def _check_materials(db, course_id: str, document_ids) -> None:
    for document_id in document_ids:
        if not db.execute("SELECT 1 FROM course_materials WHERE course_id = ? AND document_id = ?", (course_id, str(document_id))).fetchone():
            raise NotFound("Course material not found")


def list_lessons(teacher_id: str, course_id: str) -> list[dict]:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        rows = db.execute("SELECT l.* FROM lessons l JOIN topics t ON t.id = l.topic_id WHERE t.subject_id = ? ORDER BY t.position, l.position, l.title", (course["subject_id"],)).fetchall()
        return [_lesson(db, row) for row in rows]


def create_lesson(teacher_id: str, course_id: str, request: CourseLessonInput) -> dict:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        _course_topic(db, course, str(request.topic_id))
        _check_materials(db, course_id, request.source_document_ids)
        lesson_id, created = str(uuid4()), now()
        try:
            db.execute("INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       (lesson_id, str(request.topic_id), request.title, request.summary, request.body, request.difficulty, request.position, created, created))
        except sqlite3.IntegrityError as error:
            raise Conflict("A lesson with this title already exists in the topic") from error
        db.executemany("INSERT INTO lesson_objectives VALUES (?, ?, ?)",
                       [(lesson_id, index, objective) for index, objective in enumerate(request.objectives)])
        db.executemany("INSERT INTO lesson_documents VALUES (?, ?)",
                       [(lesson_id, str(document_id)) for document_id in request.source_document_ids])
        return _lesson(db, db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone())


def update_lesson(teacher_id: str, course_id: str, lesson_id: str, request: CourseLessonInput) -> dict:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        _course_topic(db, course, str(request.topic_id))
        existing = db.execute("SELECT l.id FROM lessons l JOIN topics t ON t.id = l.topic_id WHERE l.id = ? AND t.subject_id = ?", (lesson_id, course["subject_id"])).fetchone()
        if not existing:
            raise NotFound("Lesson not found in this course")
        _check_materials(db, course_id, request.source_document_ids)
        try:
            db.execute("UPDATE lessons SET topic_id = ?, title = ?, summary = ?, body = ?, difficulty = ?, position = ?, updated_at = ? WHERE id = ?",
                       (str(request.topic_id), request.title, request.summary, request.body, request.difficulty, request.position, now(), lesson_id))
        except sqlite3.IntegrityError as error:
            raise Conflict("A lesson with this title already exists in the topic") from error
        db.execute("DELETE FROM lesson_objectives WHERE lesson_id = ?", (lesson_id,))
        db.execute("DELETE FROM lesson_documents WHERE lesson_id = ?", (lesson_id,))
        db.executemany("INSERT INTO lesson_objectives VALUES (?, ?, ?)",
                       [(lesson_id, index, objective) for index, objective in enumerate(request.objectives)])
        db.executemany("INSERT INTO lesson_documents VALUES (?, ?)",
                       [(lesson_id, str(document_id)) for document_id in request.source_document_ids])
        return _lesson(db, db.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone())


def add_material(teacher_id: str, course_id: str, document: dict) -> dict:
    with database() as db:
        _course(db, teacher_id, course_id)
        material_id = str(uuid4())
        db.execute("INSERT INTO course_materials VALUES (?, ?, ?, ?, ?, '', ?)",
                   (material_id, course_id, document["document_id"], document["filename"], document["filename"], now()))
        return dict(db.execute("SELECT * FROM course_materials WHERE id = ?", (material_id,)).fetchone())


def list_materials(teacher_id: str, course_id: str) -> list[dict]:
    with database() as db:
        _course(db, teacher_id, course_id)
        return [dict(row) for row in db.execute("SELECT * FROM course_materials WHERE course_id = ? ORDER BY uploaded_at DESC", (course_id,))]


def get_material(teacher_id: str, course_id: str, material_id: str) -> dict:
    with database() as db:
        _course(db, teacher_id, course_id)
        row = db.execute("SELECT * FROM course_materials WHERE id = ? AND course_id = ?", (material_id, course_id)).fetchone()
        if not row:
            raise NotFound("Material not found")
        return dict(row)


def update_material(teacher_id: str, course_id: str, material_id: str, title: str, description: str) -> dict:
    with database() as db:
        _course(db, teacher_id, course_id)
        row = db.execute("SELECT * FROM course_materials WHERE id = ? AND course_id = ?", (material_id, course_id)).fetchone()
        if not row:
            raise NotFound("Material not found")
        db.execute("UPDATE course_materials SET title = ?, description = ? WHERE id = ?", (title, description, material_id))
        return dict(db.execute("SELECT * FROM course_materials WHERE id = ?", (material_id,)).fetchone())


def remove_material(teacher_id: str, course_id: str, material_id: str) -> dict:
    with database() as db:
        _course(db, teacher_id, course_id)
        row = db.execute("SELECT * FROM course_materials WHERE id = ? AND course_id = ?", (material_id, course_id)).fetchone()
        if not row:
            raise NotFound("Material not found")
        db.execute("DELETE FROM lesson_documents WHERE document_id = ?", (row["document_id"],))
        db.execute("DELETE FROM course_materials WHERE id = ?", (material_id,))
        return dict(row)


def is_managed_document(document_id: str) -> bool:
    from app.services import memory_service

    if not memory_service.DB_PATH.exists():
        return False
    with closing(sqlite3.connect(memory_service.DB_PATH)) as db:
        db.execute("PRAGMA query_only = ON")
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'course_materials'").fetchone():
            return False
        return db.execute("SELECT 1 FROM course_materials WHERE document_id = ?", (document_id,)).fetchone() is not None


def student_can_use_document(student_id: str, document_id: str) -> bool:
    with database() as db:
        managed = db.execute("SELECT course_id FROM course_materials WHERE document_id = ?", (document_id,)).fetchone()
        if not managed:
            return True
        return db.execute("SELECT 1 FROM course_enrollments WHERE course_id = ? AND student_id = ?", (managed["course_id"], student_id)).fetchone() is not None


def list_students(teacher_id: str, course_id: str) -> list[dict]:
    with database() as db:
        _course(db, teacher_id, course_id)
        return [dict(row) for row in db.execute(
            "SELECT u.id, u.email, p.display_name, e.enrolled_at FROM course_enrollments e JOIN users u ON u.id = e.student_id "
            "JOIN student_profiles p ON p.user_id = u.id WHERE e.course_id = ? ORDER BY p.display_name", (course_id,))]


def enroll_student(teacher_id: str, course_id: str, email: str) -> dict:
    with database() as db:
        _course(db, teacher_id, course_id)
        user = db.execute("SELECT id, email FROM users WHERE email = ? COLLATE NOCASE AND role = 'student'", (email.strip(),)).fetchone()
        if not user:
            raise NotFound("Student account not found")
        db.execute("INSERT OR IGNORE INTO course_enrollments VALUES (?, ?, ?)", (course_id, user["id"], now()))
        return dict(db.execute("SELECT u.id, u.email, p.display_name, e.enrolled_at FROM course_enrollments e JOIN users u ON u.id = e.student_id JOIN student_profiles p ON p.user_id = u.id WHERE e.course_id = ? AND e.student_id = ?", (course_id, user["id"])).fetchone())


def remove_student(teacher_id: str, course_id: str, student_id: str) -> None:
    with database() as db:
        _course(db, teacher_id, course_id)
        deleted = db.execute("DELETE FROM course_enrollments WHERE course_id = ? AND student_id = ?", (course_id, student_id)).rowcount
        if not deleted:
            raise NotFound("Enrollment not found")
        db.execute("DELETE FROM quiz_assignments WHERE student_id = ? AND teacher_quiz_id IN (SELECT id FROM teacher_quizzes WHERE course_id = ?)", (student_id, course_id))


def _quiz_record(db, teacher_id: str, quiz_id: str):
    row = db.execute("SELECT q.* FROM teacher_quizzes q JOIN courses c ON c.id = q.course_id WHERE q.id = ? AND c.teacher_id = ?", (quiz_id, teacher_id)).fetchone()
    if not row:
        raise NotFound("Quiz not found")
    return row


def _quiz_dict(row) -> dict:
    return {key: row[key] for key in ("id", "course_id", "topic_id", "status", "created_at", "updated_at", "published_at")} | {"response": QuizResponse.model_validate_json(row["quiz_json"]).model_dump(mode="json")}


def list_quizzes(teacher_id: str, course_id: str) -> list[dict]:
    with database() as db:
        _course(db, teacher_id, course_id)
        return [_quiz_dict(row) for row in db.execute("SELECT * FROM teacher_quizzes WHERE course_id = ? ORDER BY created_at DESC", (course_id,))]


def save_quiz(teacher_id: str, course_id: str, request: TeacherQuizInput, sources=None) -> dict:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        if request.topic_id:
            _course_topic(db, course, str(request.topic_id))
        quiz_id, created = str(uuid4()), now()
        response = QuizResponse(quiz=request.quiz, sources=sources or [])
        db.execute("INSERT INTO teacher_quizzes VALUES (?, ?, ?, ?, 'draft', ?, ?, NULL)",
                   (quiz_id, course_id, str(request.topic_id) if request.topic_id else None, response.model_dump_json(), created, created))
        return _quiz_dict(_quiz_record(db, teacher_id, quiz_id))


def update_quiz(teacher_id: str, quiz_id: str, request: TeacherQuizInput) -> dict:
    with database() as db:
        row = _quiz_record(db, teacher_id, quiz_id)
        if row["status"] != "draft":
            raise Conflict("Published quizzes cannot be edited")
        course = _course(db, teacher_id, row["course_id"])
        if request.topic_id:
            _course_topic(db, course, str(request.topic_id))
        previous = QuizResponse.model_validate_json(row["quiz_json"])
        response = QuizResponse(quiz=request.quiz, sources=previous.sources)
        db.execute("UPDATE teacher_quizzes SET topic_id = ?, quiz_json = ?, updated_at = ? WHERE id = ?",
                   (str(request.topic_id) if request.topic_id else None, response.model_dump_json(), now(), quiz_id))
        return _quiz_dict(_quiz_record(db, teacher_id, quiz_id))


def publish_quiz(teacher_id: str, quiz_id: str) -> dict:
    with database() as db:
        row = _quiz_record(db, teacher_id, quiz_id)
        if row["status"] == "draft":
            published = now()
            db.execute("UPDATE teacher_quizzes SET status = 'published', published_at = ?, updated_at = ? WHERE id = ?", (published, published, quiz_id))
        return _quiz_dict(_quiz_record(db, teacher_id, quiz_id))


def assign_quiz(teacher_id: str, quiz_id: str, student_ids: list[str]) -> dict:
    with database() as db:
        row = _quiz_record(db, teacher_id, quiz_id)
        if row["status"] != "published":
            raise Conflict("Publish the quiz before assigning it")
        enrolled = {item[0] for item in db.execute("SELECT student_id FROM course_enrollments WHERE course_id = ?", (row["course_id"],))}
        targets = student_ids or sorted(enrolled)
        if not targets:
            raise Conflict("Enroll students before assigning a quiz")
        if any(student_id not in enrolled for student_id in targets):
            raise NotFound("Student is not enrolled in this course")
        topic = db.execute("SELECT title FROM topics WHERE id = ?", (row["topic_id"],)).fetchone() if row["topic_id"] else None
        response = QuizResponse.model_validate_json(row["quiz_json"])
        topic_title = topic["title"] if topic else response.quiz.title
        added = 0
        for student_id in targets:
            if db.execute("SELECT 1 FROM quiz_assignments WHERE teacher_quiz_id = ? AND student_id = ?", (quiz_id, student_id)).fetchone():
                continue
            practice_id, assigned = str(uuid4()), now()
            db.execute("INSERT INTO practice_quizzes (id, student_id, topic, quiz_json, created_at, teacher_quiz_id) VALUES (?, ?, ?, ?, ?, ?)",
                       (practice_id, student_id, topic_title, response.model_dump_json(), assigned, quiz_id))
            db.execute("INSERT INTO quiz_assignments VALUES (?, ?, ?, ?, ?)", (str(uuid4()), quiz_id, student_id, practice_id, assigned))
            added += 1
        return {"assigned": added, "total": len(targets)}


def quiz_results(teacher_id: str, quiz_id: str) -> list[dict]:
    with database() as db:
        row = _quiz_record(db, teacher_id, quiz_id)
        results = []
        for item in db.execute(
            "SELECT u.id AS student_id, u.email, p.display_name, qa.assigned_at, a.id AS attempt_id, a.score, a.max_score, a.created_at "
            "FROM quiz_assignments qa JOIN users u ON u.id = qa.student_id JOIN student_profiles p ON p.user_id = u.id "
            "JOIN course_enrollments e ON e.student_id = u.id AND e.course_id = ? "
            "LEFT JOIN quiz_attempts a ON a.quiz_id = qa.practice_quiz_id AND a.student_id = qa.student_id "
            "WHERE qa.teacher_quiz_id = ? ORDER BY p.display_name", (row["course_id"], quiz_id)):
            record = dict(item)
            record["answers"] = [dict(answer) for answer in db.execute(
                "SELECT question_index, submitted_answer, correct, points, provisional FROM attempt_answers WHERE attempt_id = ? ORDER BY question_index", (item["attempt_id"],))] if item["attempt_id"] else []
            results.append(record)
        return results
