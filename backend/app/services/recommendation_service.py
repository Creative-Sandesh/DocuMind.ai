"""Explainable student recommendations from owned progress and due reviews."""

import sqlite3

from app.services.database import database
from app.services.knowledge_profile_service import _profiles
from app.services.spaced_repetition_service import due_summary


def _recommendations(db: sqlite3.Connection, student_id: str, profiles: list[dict] | None = None) -> list[dict]:
    profiles = profiles if profiles is not None else _profiles(db, student_id)["topics"]
    items = []
    due = due_summary(db, student_id)["due_count"]
    if due:
        items.append({"type": "review_flashcards", "title": "Review due flashcards",
                      "reason": f"{due} saved card(s) are scheduled for review now.", "due_count": due})
    assignment = db.execute(
        "SELECT qa.id, c.title AS course_title FROM quiz_assignments qa "
        "JOIN teacher_quizzes tq ON tq.id = qa.teacher_quiz_id "
        "JOIN courses c ON c.id = tq.course_id "
        "JOIN course_enrollments e ON e.course_id = c.id AND e.student_id = qa.student_id "
        "WHERE qa.student_id = ? AND NOT EXISTS "
        "(SELECT 1 FROM quiz_attempts a WHERE a.quiz_id = qa.practice_quiz_id AND a.student_id = qa.student_id) "
        "ORDER BY qa.assigned_at LIMIT 1", (student_id,)).fetchone()
    if assignment:
        items.append({"type": "attempt_quiz", "title": "Take your assigned quiz",
                      "reason": f"An assigned quiz in {assignment['course_title']} has not been attempted.",
                      "assignment_id": assignment["id"]})
    weak = sorted((profile for profile in profiles if profile["status"] == "weak"),
                  key=lambda item: (item["mastery_percent"], item["topic_key"]))
    for profile in weak[:2]:
        items.append({"type": "practice_weak_topic", "title": f"Practice {profile['topic']}",
                      "reason": profile["status_reason"], "topic": profile["topic"],
                      "topic_key": profile["topic_key"]})
    weak_ids = [profile["topic_id"] for profile in weak if profile["topic_id"]]
    if weak_ids:
        placeholders = ",".join("?" for _ in weak_ids)
        row = db.execute(
            "SELECT l.id, l.title FROM lessons l JOIN lesson_progress lp ON lp.lesson_id = l.id "
            "JOIN topics t ON t.id = l.topic_id LEFT JOIN courses c ON c.subject_id = t.subject_id "
            "LEFT JOIN course_enrollments e ON e.course_id = c.id AND e.student_id = ? "
            f"WHERE lp.student_id = ? AND l.topic_id IN ({placeholders}) "
            "AND (c.id IS NULL OR e.student_id IS NOT NULL) ORDER BY lp.completed_at DESC LIMIT 1",
            (student_id, student_id, *weak_ids)).fetchone()
        if row:
            items.append({"type": "revisit_lesson", "title": f"Revisit {row['title']}",
                          "reason": "You completed this lesson, but its topic now needs review.",
                          "lesson_id": row["id"]})
    next_lesson = db.execute(
        "SELECT l.id, l.title FROM lessons l JOIN topics t ON t.id = l.topic_id "
        "LEFT JOIN courses c ON c.subject_id = t.subject_id "
        "LEFT JOIN course_enrollments e ON e.course_id = c.id AND e.student_id = ? "
        "LEFT JOIN lesson_progress lp ON lp.lesson_id = l.id AND lp.student_id = ? "
        "WHERE lp.lesson_id IS NULL AND (c.id IS NULL OR e.student_id IS NOT NULL) "
        "ORDER BY c.title, t.position, l.position, l.title LIMIT 1",
        (student_id, student_id)).fetchone()
    if next_lesson:
        items.append({"type": "next_lesson", "title": f"Read {next_lesson['title']}",
                      "reason": "This is an available lesson you have not completed.",
                      "lesson_id": next_lesson["id"]})
    if not assignment:
        candidate = next((profile for profile in profiles if profile["status"] in ("developing", "insufficient_evidence")), None)
        if candidate:
            items.append({"type": "attempt_quiz", "title": f"Try a quiz on {candidate['topic']}",
                          "reason": candidate["status_reason"], "topic": candidate["topic"],
                          "topic_key": candidate["topic_key"]})
    return items[:7]


def recommendations(student_id: str) -> list[dict]:
    with database() as db:
        return _recommendations(db, student_id)
