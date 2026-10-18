"""Owned practice, lesson progress, real study time, and dashboard queries."""

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.learning_tools import QuizEvaluationRequest, QuizResponse
from app.schemas.student import AttemptRequest, KnowledgeProfileResponse
from app.services.auth_service import now
from app.services.database import database
from app.services.knowledge_profile_service import _profiles
from app.services.recommendation_service import _recommendations
from app.services.spaced_repetition_service import due_summary
from app.services.learning_tools_service import evaluate_quiz


class StudentNotFoundError(Exception):
    pass


class StudentConflictError(Exception):
    pass


def save_quiz(student_id: str, topic: str, response: QuizResponse, topic_id: str | None = None) -> dict:
    quiz_id = str(uuid4())
    with database() as db:
        db.execute("INSERT INTO practice_quizzes (id, student_id, topic, quiz_json, created_at, personalized_topic_id) VALUES (?, ?, ?, ?, ?, ?)",
                   (quiz_id, student_id, topic.strip(), response.model_dump_json(), now(), topic_id))
    return {"quiz_id": quiz_id, "response": response}


def submit_attempt(student_id: str, quiz_id: str, request: AttemptRequest) -> dict:
    with database() as db:
        row = db.execute("SELECT quiz_json, topic, teacher_quiz_id FROM practice_quizzes WHERE id = ? AND student_id = ?", (quiz_id, student_id)).fetchone()
        if not row:
            raise StudentNotFoundError("Quiz not found")
        if row["teacher_quiz_id"]:
            assignment = db.execute(
                "SELECT 1 FROM quiz_assignments qa JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
                "JOIN course_enrollments e ON e.student_id = qa.student_id AND e.course_id = tq.course_id "
                "WHERE qa.practice_quiz_id = ? AND qa.student_id = ?", (quiz_id, student_id)).fetchone()
            if not assignment:
                raise StudentNotFoundError("Assignment not found")
            if db.execute("SELECT 1 FROM quiz_attempts WHERE quiz_id = ? AND student_id = ?", (quiz_id, student_id)).fetchone():
                raise StudentConflictError("This assigned quiz was already submitted")
        quiz = QuizResponse.model_validate_json(row["quiz_json"]).quiz
        result = evaluate_quiz(QuizEvaluationRequest(quiz=quiz, answers=request.answers))
        attempt_id, created_at = str(uuid4()), now()
        db.execute("INSERT INTO quiz_attempts VALUES (?, ?, ?, ?, ?, ?)",
                   (attempt_id, quiz_id, student_id, result.score, result.max_score, created_at))
        db.executemany("INSERT INTO attempt_answers VALUES (?, ?, ?, ?, ?, ?)", [
            (attempt_id, item.question_index, item.submitted_answer, int(item.correct), item.points, int(item.provisional))
            for item in result.results
        ])
        return {"id": attempt_id, "quiz_id": quiz_id, "topic": row["topic"], "created_at": created_at, "evaluation": result}


def get_attempt(student_id: str, attempt_id: str) -> dict:
    with database() as db:
        row = db.execute("SELECT a.*, q.topic FROM quiz_attempts a JOIN practice_quizzes q ON q.id = a.quiz_id WHERE a.id = ? AND a.student_id = ?", (attempt_id, student_id)).fetchone()
        if not row:
            raise StudentNotFoundError("Attempt not found")
        answers = [dict(item) for item in db.execute("SELECT question_index, submitted_answer, correct, points, provisional FROM attempt_answers WHERE attempt_id = ? ORDER BY question_index", (attempt_id,))]
        return {**dict(row), "answers": answers}


def list_attempts(student_id: str, limit: int, offset: int) -> list[dict]:
    with database() as db:
        return [dict(row) for row in db.execute(
            "SELECT a.id, a.quiz_id, q.topic, a.score, a.max_score, a.created_at "
            "FROM quiz_attempts a JOIN practice_quizzes q ON q.id = a.quiz_id "
            "WHERE a.student_id = ? ORDER BY a.created_at DESC, a.id DESC LIMIT ? OFFSET ?",
            (student_id, limit, offset),
        )]


def complete_lesson(student_id: str, lesson_id: str) -> dict:
    with database() as db:
        lesson = db.execute(
            "SELECT l.id, l.title FROM lessons l JOIN topics t ON t.id = l.topic_id "
            "LEFT JOIN courses c ON c.subject_id = t.subject_id "
            "LEFT JOIN course_enrollments e ON e.course_id = c.id AND e.student_id = ? "
            "WHERE l.id = ? AND (c.id IS NULL OR e.student_id IS NOT NULL)", (student_id, lesson_id)).fetchone()
        if not lesson:
            raise StudentNotFoundError("Lesson not found")
        db.execute("INSERT OR IGNORE INTO lesson_progress VALUES (?, ?, ?)", (student_id, lesson_id, now()))
        row = db.execute("SELECT completed_at FROM lesson_progress WHERE student_id = ? AND lesson_id = ?", (student_id, lesson_id)).fetchone()
        return {"lesson_id": lesson_id, "title": lesson["title"], "completed_at": row["completed_at"]}


def available_lessons(student_id: str) -> list[dict]:
    with database() as db:
        return [dict(row) for row in db.execute(
            "SELECT l.id, l.title, l.summary, c.title AS course_title FROM lessons l JOIN topics t ON t.id = l.topic_id "
            "LEFT JOIN courses c ON c.subject_id = t.subject_id "
            "LEFT JOIN course_enrollments e ON e.course_id = c.id AND e.student_id = ? "
            "WHERE c.id IS NULL OR e.student_id IS NOT NULL ORDER BY c.title, t.position, l.position, l.title", (student_id,))]


def start_study(student_id: str, course_id: str | None = None) -> dict:
    with database() as db:
        if course_id and not db.execute("SELECT 1 FROM course_enrollments WHERE course_id = ? AND student_id = ?", (course_id, student_id)).fetchone():
            raise StudentNotFoundError("Course enrollment not found")
        row = db.execute("SELECT * FROM study_sessions WHERE student_id = ? AND ended_at IS NULL", (student_id,)).fetchone()
        if row:
            return dict(row)
        session = {"id": str(uuid4()), "student_id": student_id, "started_at": now(), "ended_at": None, "duration_seconds": None, "course_id": course_id}
        db.execute("INSERT INTO study_sessions (id, student_id, started_at, ended_at, duration_seconds, course_id) VALUES (?, ?, ?, ?, ?, ?)", tuple(session.values()))
        return session


def end_study(student_id: str, session_id: str) -> dict:
    with database() as db:
        row = db.execute("SELECT * FROM study_sessions WHERE id = ? AND student_id = ?", (session_id, student_id)).fetchone()
        if not row:
            raise StudentNotFoundError("Study session not found")
        if row["ended_at"]:
            return dict(row)
        ended = datetime.now(timezone.utc)
        started = datetime.fromisoformat(row["started_at"])
        duration = max(0, int((ended - started).total_seconds()))
        db.execute("UPDATE study_sessions SET ended_at = ?, duration_seconds = ? WHERE id = ?", (ended.isoformat(), duration, session_id))
        return {**dict(row), "ended_at": ended.isoformat(), "duration_seconds": duration}


def dashboard(student_id: str) -> dict:
    with database() as db:
        courses = [dict(row) for row in db.execute(
            "SELECT c.id, c.title, c.description, e.enrolled_at FROM course_enrollments e JOIN courses c ON c.id = e.course_id WHERE e.student_id = ? ORDER BY e.enrolled_at DESC", (student_id,))]
        lessons = [dict(row) for row in db.execute(
            "SELECT l.id, l.title, lp.completed_at FROM lesson_progress lp JOIN lessons l ON l.id = lp.lesson_id WHERE lp.student_id = ? ORDER BY lp.completed_at DESC", (student_id,))]
        attempts = [dict(row) for row in db.execute(
            "SELECT a.id, a.quiz_id, q.topic, a.score, a.max_score, a.created_at FROM quiz_attempts a JOIN practice_quizzes q ON q.id = a.quiz_id WHERE a.student_id = ? ORDER BY a.created_at DESC, a.id DESC LIMIT 20", (student_id,))]
        total_attempts = db.execute("SELECT COUNT(*) FROM quiz_attempts WHERE student_id = ?", (student_id,)).fetchone()[0]
        sessions = [dict(row) for row in db.execute(
            "SELECT ss.id, ss.started_at, ss.ended_at, ss.duration_seconds, ss.course_id, c.title AS course_title "
            "FROM study_sessions ss LEFT JOIN courses c ON c.id = ss.course_id WHERE ss.student_id = ? ORDER BY ss.started_at DESC LIMIT 30", (student_id,))]
        topics = [dict(row) for row in db.execute(
            "SELECT q.topic, COUNT(*) AS attempts, SUM(a.score) AS score, SUM(a.max_score) AS max_score "
            "FROM quiz_attempts a JOIN practice_quizzes q ON q.id = a.quiz_id WHERE a.student_id = ? "
            "GROUP BY lower(q.topic) ORDER BY q.topic", (student_id,))]
        total_study_seconds = db.execute("SELECT COALESCE(SUM(duration_seconds), 0) FROM study_sessions WHERE student_id = ?", (student_id,)).fetchone()[0]
        knowledge_profile = KnowledgeProfileResponse.model_validate(_profiles(db, student_id)).model_dump(mode="json")
        return {
            "courses": courses, "lessons_completed": lessons, "quiz_attempts": attempts,
            "total_attempts": total_attempts, "total_study_seconds": total_study_seconds,
            "study_sessions": sessions, "topic_progress": topics,
            "knowledge_profile": knowledge_profile,
            "review_summary": due_summary(db, student_id),
            "recommendations": _recommendations(db, student_id, knowledge_profile["topics"]),
        }


def assigned_quizzes(student_id: str) -> list[dict]:
    with database() as db:
        rows = db.execute(
            "SELECT qa.id, qa.practice_quiz_id, qa.assigned_at, tq.course_id, c.title AS course_title, pq.quiz_json, "
            "(SELECT a.id FROM quiz_attempts a WHERE a.quiz_id = qa.practice_quiz_id AND a.student_id = qa.student_id LIMIT 1) AS attempt_id "
            "FROM quiz_assignments qa JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
            "JOIN courses c ON c.id = tq.course_id JOIN practice_quizzes pq ON pq.id = qa.practice_quiz_id "
            "JOIN course_enrollments e ON e.student_id = qa.student_id AND e.course_id = tq.course_id "
            "WHERE qa.student_id = ? ORDER BY qa.assigned_at DESC", (student_id,)).fetchall()
        assignments = []
        for row in rows:
            quiz = QuizResponse.model_validate_json(row["quiz_json"]).quiz
            assignments.append({
                "id": row["id"], "practice_quiz_id": row["practice_quiz_id"], "assigned_at": row["assigned_at"],
                "course_id": row["course_id"], "course_title": row["course_title"], "title": quiz.title,
                "attempt_id": row["attempt_id"],
                "questions": [{"type": q.type, "question": q.question, "options": q.options} for q in quiz.questions],
            })
        return assignments


def enrolled_materials(student_id: str, course_id: str) -> list[dict]:
    with database() as db:
        if not db.execute("SELECT 1 FROM course_enrollments WHERE course_id = ? AND student_id = ?", (course_id, student_id)).fetchone():
            raise StudentNotFoundError("Course enrollment not found")
        return [dict(row) for row in db.execute("SELECT id, document_id, filename, title, description, uploaded_at FROM course_materials WHERE course_id = ? ORDER BY uploaded_at DESC", (course_id,))]


def enrolled_material(student_id: str, course_id: str, material_id: str) -> dict:
    with database() as db:
        row = db.execute("SELECT m.* FROM course_materials m JOIN course_enrollments e ON e.course_id = m.course_id "
                         "WHERE m.id = ? AND m.course_id = ? AND e.student_id = ?", (material_id, course_id, student_id)).fetchone()
        if not row:
            raise StudentNotFoundError("Course material not found")
        return dict(row)


def available_lesson(student_id: str, lesson_id: str) -> dict:
    with database() as db:
        row = db.execute(
            "SELECT l.* FROM lessons l JOIN topics t ON t.id = l.topic_id "
            "LEFT JOIN courses c ON c.subject_id = t.subject_id "
            "LEFT JOIN course_enrollments e ON e.course_id = c.id AND e.student_id = ? "
            "WHERE l.id = ? AND (c.id IS NULL OR e.student_id IS NOT NULL)", (student_id, lesson_id)).fetchone()
        if not row:
            raise StudentNotFoundError("Lesson not found")
        from app.services.learning_content_service import _lesson
        return _lesson(db, row)
