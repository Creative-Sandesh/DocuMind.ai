"""Real course-scoped aggregations over enrollments, attempts and study sessions."""

from app.services.database import database
from app.services.teacher_service import _course


def course_analytics(teacher_id: str, course_id: str) -> dict:
    with database() as db:
        course = _course(db, teacher_id, course_id)
        subject_id = course["subject_id"]
        total_lessons = db.execute(
            "SELECT COUNT(*) FROM lessons l JOIN topics t ON t.id = l.topic_id WHERE t.subject_id = ?", (subject_id,)).fetchone()[0]
        students = [dict(row) for row in db.execute(
            "SELECT u.id, u.email, p.display_name, "
            "(SELECT COUNT(*) FROM lesson_progress lp JOIN lessons l ON l.id = lp.lesson_id JOIN topics t ON t.id = l.topic_id "
            " WHERE lp.student_id = u.id AND t.subject_id = ?) AS lessons_completed, "
            "(SELECT COUNT(*) FROM quiz_assignments qa JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
            " WHERE qa.student_id = u.id AND tq.course_id = ?) AS quizzes_assigned, "
            "(SELECT COUNT(DISTINCT qa.id) FROM quiz_assignments qa JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
            " JOIN quiz_attempts a ON a.quiz_id = qa.practice_quiz_id WHERE qa.student_id = u.id AND tq.course_id = ?) AS quizzes_completed, "
            "(SELECT COALESCE(SUM(duration_seconds), 0) FROM study_sessions ss WHERE ss.student_id = u.id AND ss.course_id = ?) AS study_seconds "
            "FROM course_enrollments e JOIN users u ON u.id = e.student_id JOIN student_profiles p ON p.user_id = u.id "
            "WHERE e.course_id = ? ORDER BY p.display_name",
            (subject_id, course_id, course_id, course_id, course_id),
        )]
        assignment_count = db.execute(
            "SELECT COUNT(*) FROM quiz_assignments qa JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
            "JOIN course_enrollments e ON e.student_id = qa.student_id AND e.course_id = tq.course_id WHERE tq.course_id = ?", (course_id,)).fetchone()[0]
        completed_count = db.execute(
            "SELECT COUNT(DISTINCT qa.id) FROM quiz_assignments qa JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
            "JOIN course_enrollments e ON e.student_id = qa.student_id AND e.course_id = tq.course_id "
            "JOIN quiz_attempts a ON a.quiz_id = qa.practice_quiz_id WHERE tq.course_id = ?", (course_id,)).fetchone()[0]
        score_row = db.execute(
            "SELECT COUNT(a.id), COALESCE(SUM(a.score), 0), COALESCE(SUM(a.max_score), 0) "
            "FROM quiz_attempts a JOIN quiz_assignments qa ON qa.practice_quiz_id = a.quiz_id "
            "JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
            "JOIN course_enrollments e ON e.student_id = qa.student_id AND e.course_id = tq.course_id "
            "WHERE tq.course_id = ?", (course_id,)).fetchone()
        topics = [dict(row) for row in db.execute(
            "SELECT COALESCE(t.title, pq.topic) AS topic, COUNT(a.id) AS attempts, SUM(a.score) AS score, SUM(a.max_score) AS max_score, "
            "ROUND(100.0 * SUM(a.score) / SUM(a.max_score), 1) AS average_percent "
            "FROM quiz_attempts a JOIN quiz_assignments qa ON qa.practice_quiz_id = a.quiz_id "
            "JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id JOIN practice_quizzes pq ON pq.id = qa.practice_quiz_id "
            "JOIN course_enrollments e ON e.student_id = qa.student_id AND e.course_id = tq.course_id "
            "LEFT JOIN topics t ON t.id = tq.topic_id WHERE tq.course_id = ? "
            "GROUP BY COALESCE(t.title, pq.topic) ORDER BY average_percent, topic", (course_id,))]
        weak = [dict(row) for row in db.execute(
            "SELECT topic, COUNT(*) AS students FROM ("
            "SELECT qa.student_id, COALESCE(t.title, pq.topic) AS topic, COUNT(a.id) AS attempts, "
            "1.0 * SUM(a.score) / SUM(a.max_score) AS ratio "
            "FROM quiz_attempts a JOIN quiz_assignments qa ON qa.practice_quiz_id = a.quiz_id "
            "JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id JOIN practice_quizzes pq ON pq.id = qa.practice_quiz_id "
            "JOIN course_enrollments e ON e.student_id = qa.student_id AND e.course_id = tq.course_id "
            "LEFT JOIN topics t ON t.id = tq.topic_id WHERE tq.course_id = ? "
            "GROUP BY qa.student_id, COALESCE(t.title, pq.topic) HAVING attempts >= 2 AND ratio < 0.6"
            ") GROUP BY topic ORDER BY students DESC, topic", (course_id,))]
        for student in students:
            student["total_lessons"] = total_lessons
        return {
            "course_id": course_id,
            "summary": {
                "students": len(students), "total_lessons": total_lessons,
                "assignments": assignment_count, "completed_assignments": completed_count,
                "completion_rate_percent": round(100 * completed_count / assignment_count, 1) if assignment_count else None,
                "graded_attempts": score_row[0],
                "average_score_percent": round(100 * score_row[1] / score_row[2], 1) if score_row[2] else None,
                "study_seconds": sum(student["study_seconds"] for student in students),
            },
            "students": students, "topics": topics, "weak_topic_distribution": weak,
            "weak_topic_rule": "At least two assigned quiz attempts in a topic and below 60% total points.",
            "study_time_scope": "Only study sessions started for this course by currently enrolled students.",
        }
