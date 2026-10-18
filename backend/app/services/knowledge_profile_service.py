"""Explainable, student-scoped topic knowledge summaries from saved attempts."""

import sqlite3

from app.services.database import database
from app.services.adaptive_learning_service import assess_topic, recommend_difficulty


RECENT_ATTEMPTS = 3
SUPPORTED_MIN_ATTEMPTS = 2
SUPPORTED_MIN_OBJECTIVE_ANSWERS = 5
METHOD = (
    "Only non-provisional answers count toward accuracy. Mastery is 60% accuracy "
    "over the most recent three attempts plus 40% accuracy over all attempts. "
    "If recent attempts have no objective answers, overall accuracy is used. "
    "Evidence is supported after at least two attempts and five objective answers."
)


def _percent(correct: int, total: int) -> float | None:
    return round(100 * correct / total, 1) if total else None


def _profiles(db: sqlite3.Connection, student_id: str) -> dict:
    rows = db.execute(
        "SELECT a.id AS attempt_id, a.created_at, pq.topic AS practice_topic, "
        "COALESCE(tq.topic_id, pq.personalized_topic_id) AS topic_id, t.title AS catalog_topic, aa.correct, aa.provisional "
        "FROM quiz_attempts a JOIN practice_quizzes pq ON pq.id = a.quiz_id "
        "LEFT JOIN teacher_quizzes tq ON tq.id = pq.teacher_quiz_id "
        "LEFT JOIN topics t ON t.id = COALESCE(tq.topic_id, pq.personalized_topic_id) "
        "LEFT JOIN attempt_answers aa ON aa.attempt_id = a.id "
        "WHERE a.student_id = ? ORDER BY a.created_at DESC, a.id DESC, aa.question_index",
        (student_id,),
    )
    groups: dict[str, dict] = {}
    for row in rows:
        topic_id = row["topic_id"]
        label = row["catalog_topic"] or row["practice_topic"]
        key = f"catalog:{topic_id}" if topic_id else f"practice:{' '.join(label.casefold().split())}"
        if key not in groups:
            groups[key] = {
                "topic_key": key, "topic_id": topic_id, "topic": label,
                "last_practiced_at": row["created_at"], "attempts": {},
            }
        attempts = groups[key]["attempts"]
        if row["attempt_id"] not in attempts:
            attempts[row["attempt_id"]] = {"correct": 0, "incorrect": 0, "provisional": 0}
        attempt = attempts[row["attempt_id"]]
        if row["provisional"] is not None:
            if row["provisional"]:
                attempt["provisional"] += 1
            elif row["correct"]:
                attempt["correct"] += 1
            else:
                attempt["incorrect"] += 1

    profiles = []
    for group in groups.values():
        attempts = list(group["attempts"].values())
        correct = sum(item["correct"] for item in attempts)
        incorrect = sum(item["incorrect"] for item in attempts)
        provisional = sum(item["provisional"] for item in attempts)
        recent = attempts[:RECENT_ATTEMPTS]
        recent_correct = sum(item["correct"] for item in recent)
        recent_total = sum(item["correct"] + item["incorrect"] for item in recent)
        overall_percent = _percent(correct, correct + incorrect)
        recent_percent = _percent(recent_correct, recent_total)
        mastery = None if overall_percent is None else round(
            0.6 * (recent_percent if recent_percent is not None else overall_percent)
            + 0.4 * overall_percent, 1
        )
        profile = {
            "topic_key": group["topic_key"], "topic_id": group["topic_id"], "topic": group["topic"],
            "attempts": len(attempts), "correct_answers": correct, "incorrect_answers": incorrect,
            "provisional_answers": provisional, "recent_accuracy_percent": recent_percent,
            "mastery_percent": mastery, "last_practiced_at": group["last_practiced_at"],
            "evidence": "supported" if len(attempts) >= SUPPORTED_MIN_ATTEMPTS
            and correct + incorrect >= SUPPORTED_MIN_OBJECTIVE_ANSWERS else "early",
        }
        profile.update(assess_topic(profile))
        profile["recommended_difficulty"] = recommend_difficulty(profile["status"], "intermediate")["effective_difficulty"]
        profiles.append(profile)
    profiles.sort(key=lambda item: (item["last_practiced_at"], item["topic_key"]), reverse=True)
    return {"topics": profiles, "recent_window": RECENT_ATTEMPTS, "method": METHOD}


def knowledge_profile(student_id: str) -> dict:
    with database() as db:
        return _profiles(db, student_id)
