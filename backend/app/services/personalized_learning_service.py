"""Select a student's practice focus from owned mistakes and available lessons."""

import sqlite3

from app.schemas.learning_tools import QuizResponse
from app.services.adaptive_learning_service import recommend_difficulty
from app.services.database import database
from app.services.knowledge_profile_service import _profiles


def _available_catalog_topics(db: sqlite3.Connection, student_id: str) -> list[dict]:
    return [dict(row) for row in db.execute(
        "SELECT t.id, t.title, t.description, s.title AS subject FROM topics t "
        "JOIN subjects s ON s.id = t.subject_id "
        "LEFT JOIN courses c ON c.subject_id = s.id "
        "LEFT JOIN course_enrollments e ON e.course_id = c.id AND e.student_id = ? "
        "WHERE (c.id IS NULL OR e.student_id IS NOT NULL) "
        "AND EXISTS (SELECT 1 FROM lessons l WHERE l.topic_id = t.id) "
        "ORDER BY s.title, t.position, t.title", (student_id,))]


def _missed_questions(db: sqlite3.Connection, student_id: str, topic_key: str) -> list[str]:
    rows = db.execute(
        "SELECT aa.question_index, pq.quiz_json, pq.topic AS practice_topic, "
        "COALESCE(tq.topic_id, pq.personalized_topic_id) AS topic_id "
        "FROM attempt_answers aa JOIN quiz_attempts a ON a.id = aa.attempt_id "
        "JOIN practice_quizzes pq ON pq.id = a.quiz_id "
        "LEFT JOIN teacher_quizzes tq ON tq.id = pq.teacher_quiz_id "
        "WHERE a.student_id = ? AND aa.correct = 0 AND aa.provisional = 0 "
        "ORDER BY a.created_at DESC, a.id DESC LIMIT 100", (student_id,)).fetchall()
    missed, seen = [], set()
    for row in rows:
        key = f"catalog:{row['topic_id']}" if row["topic_id"] else f"practice:{' '.join(row['practice_topic'].casefold().split())}"
        if key != topic_key:
            continue
        try:
            question = QuizResponse.model_validate_json(row["quiz_json"]).quiz.questions[row["question_index"]].question.strip()
        except (ValueError, IndexError):
            continue
        normalized = " ".join(question.casefold().split())
        if normalized not in seen:
            missed.append(question[:500])
            seen.add(normalized)
        if len(missed) == 3:
            break
    return missed


def _plan(db: sqlite3.Connection, student_id: str, requested_key: str | None = None) -> dict | None:
    profiles = _profiles(db, student_id)["topics"]
    catalog = _available_catalog_topics(db, student_id)
    allowed_ids = {item["id"] for item in catalog}
    eligible_profiles = [item for item in profiles if not item["topic_id"] or item["topic_id"] in allowed_ids]
    practiced_ids = {item["topic_id"] for item in eligible_profiles if item["topic_id"]}
    unpracticed = [item for item in catalog if item["id"] not in practiced_ids]
    selected = None
    if requested_key:
        selected = next((item for item in eligible_profiles if item["topic_key"] == requested_key), None)
        if selected is None:
            fresh = next((item for item in unpracticed if f"catalog:{item['id']}" == requested_key), None)
            if fresh:
                selected = {"topic_key": requested_key, "topic_id": fresh["id"], "topic": fresh["title"],
                            "status": "unpracticed", "mastery_percent": None}
    else:
        weak = sorted((item for item in eligible_profiles if item["status"] == "weak"),
                      key=lambda item: (item["mastery_percent"], item["topic_key"]))
        if weak:
            selected = weak[0]
        elif unpracticed:
            fresh = unpracticed[0]
            selected = {"topic_key": f"catalog:{fresh['id']}", "topic_id": fresh["id"],
                        "topic": fresh["title"], "status": "unpracticed", "mastery_percent": None}
        elif eligible_profiles:
            selected = sorted(eligible_profiles, key=lambda item: (
                item["mastery_percent"] if item["mastery_percent"] is not None else -1,
                item["topic_key"]))[0]
    if not selected:
        return None
    key, topic_id = selected["topic_key"], selected["topic_id"]
    catalog_context = next((item for item in catalog if item["id"] == topic_id), None)
    missed = _missed_questions(db, student_id, key)
    objectives = []
    if topic_id:
        objectives = [row["objective"][:300] for row in db.execute(
            "SELECT lo.objective FROM lesson_objectives lo JOIN lessons l ON l.id = lo.lesson_id "
            "WHERE l.topic_id = ? ORDER BY l.position, lo.position LIMIT 3", (topic_id,))]
    status = selected["status"]
    difficulty = ("beginner" if status == "unpracticed" else
                  recommend_difficulty(status, "intermediate")["effective_difficulty"])
    reasons = {
        "weak": "This topic has supported weak-topic evidence.",
        "unpracticed": "An available lesson topic has no saved quiz attempts.",
        "strong": "This topic is ready for more challenging practice.",
        "developing": "This topic has mixed results and needs more practice.",
        "insufficient_evidence": "This topic needs more scored practice to estimate mastery.",
    }
    reason = reasons[status]
    if missed:
        reason += f" {len(missed)} previous incorrect question(s) will guide the quiz."
    if objectives and status == "unpracticed":
        reason += " Lesson objectives will introduce new concepts."
    focus = "Create new questions that cover the topic at the requested difficulty."
    if catalog_context:
        focus += f" Subject: {catalog_context['subject'][:120]}."
        if catalog_context["description"]:
            focus += f" Topic description: {catalog_context['description'][:300]}."
    if missed:
        focus += " Revisit the concepts behind these prior incorrect questions without copying their wording: "
        focus += " | ".join(missed)
    if objectives:
        focus += " Include these lesson objectives where relevant: " + " | ".join(objectives)
    return {"topic_key": key, "topic": selected["topic"], "topic_id": topic_id,
            "status": status, "mastery_percent": selected["mastery_percent"],
            "difficulty": difficulty, "reason": reason, "prior_errors": missed,
            "lesson_objectives": objectives, "focus_context": focus}


def personalized_plan(student_id: str, requested_key: str | None = None) -> dict | None:
    with database() as db:
        return _plan(db, student_id, requested_key)
