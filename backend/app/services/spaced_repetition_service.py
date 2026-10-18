"""Owned flashcard storage and deterministic, explainable review scheduling."""

import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.schemas.learning_tools import FlashcardResponse
from app.services.database import database


class CardNotFoundError(Exception):
    pass


class CardNotDueError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def schedule(repetitions: int, interval_days: int, ease_factor: float,
             rating: str, reviewed_at: datetime) -> dict:
    """A bounded SM-2 variant: lapses return in ten minutes; successes grow in days."""
    if rating == "again":
        repetitions, interval_days = 0, 0
        ease_factor = max(1.3, ease_factor - 0.2)
        next_review = reviewed_at + timedelta(minutes=10)
    elif rating == "hard":
        repetitions += 1
        interval_days = max(1, round(interval_days * 1.2))
        ease_factor = max(1.3, ease_factor - 0.15)
        next_review = reviewed_at + timedelta(days=interval_days)
    elif rating == "good":
        repetitions += 1
        interval_days = 1 if repetitions == 1 else 3 if repetitions == 2 else max(1, round(interval_days * ease_factor))
        next_review = reviewed_at + timedelta(days=interval_days)
    elif rating == "easy":
        repetitions += 1
        interval_days = 3 if repetitions == 1 else max(4, round(max(1, interval_days) * ease_factor * 1.3))
        ease_factor = min(3.0, ease_factor + 0.15)
        next_review = reviewed_at + timedelta(days=interval_days)
    else:
        raise ValueError("Unknown review rating")
    return {"repetitions": repetitions, "interval_days": interval_days,
            "ease_factor": round(ease_factor, 2), "next_review_at": next_review.isoformat()}


def save_deck(student_id: str, topic: str, response: FlashcardResponse) -> dict:
    deck_id, created = str(uuid4()), _utc_now().isoformat()
    cards = [{"id": str(uuid4()), "index": index} for index, _ in enumerate(response.flashcards)]
    with database() as db:
        db.execute("INSERT INTO flashcard_decks VALUES (?, ?, ?, ?, ?)",
                   (deck_id, student_id, topic, response.model_dump_json(), created))
        db.executemany("INSERT INTO flashcard_cards (id, deck_id, card_index, next_review_at) VALUES (?, ?, ?, ?)",
                       [(card["id"], deck_id, card["index"], created) for card in cards])
    return {"deck_id": deck_id, "card_ids": [card["id"] for card in cards], **response.model_dump(mode="json")}


def due_summary(db: sqlite3.Connection, student_id: str, at: datetime | None = None) -> dict:
    at = at or _utc_now()
    row = db.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN c.next_review_at <= ? THEN 1 ELSE 0 END) AS due "
                     "FROM flashcard_cards c JOIN flashcard_decks d ON d.id = c.deck_id WHERE d.student_id = ?",
                     (at.isoformat(), student_id)).fetchone()
    return {"due_count": row["due"] or 0, "total_cards": row["total"]}


def due_cards(student_id: str, limit: int = 20) -> dict:
    with database() as db:
        at = _utc_now()
        rows = db.execute("SELECT c.*, d.topic, d.cards_json FROM flashcard_cards c "
                          "JOIN flashcard_decks d ON d.id = c.deck_id "
                          "WHERE d.student_id = ? AND c.next_review_at <= ? "
                          "ORDER BY c.next_review_at, c.id LIMIT ?", (student_id, at.isoformat(), limit)).fetchall()
        cards = []
        for row in rows:
            content = FlashcardResponse.model_validate_json(row["cards_json"]).flashcards[row["card_index"]]
            cards.append({"id": row["id"], "deck_id": row["deck_id"], "topic": row["topic"],
                          "front": content.front, "back": content.back, "difficulty": content.difficulty,
                          "last_reviewed_at": row["last_reviewed_at"], "next_review_at": row["next_review_at"],
                          "repetitions": row["repetitions"]})
        return {"cards": cards, "summary": due_summary(db, student_id, at)}


def review_card(student_id: str, card_id: str, rating: str) -> dict:
    with database() as db:
        row = db.execute("SELECT c.* FROM flashcard_cards c JOIN flashcard_decks d ON d.id = c.deck_id "
                         "WHERE c.id = ? AND d.student_id = ?", (card_id, student_id)).fetchone()
        if not row:
            raise CardNotFoundError("Flashcard not found")
        at = _utc_now()
        if row["next_review_at"] > at.isoformat():
            raise CardNotDueError("This flashcard is not due yet")
        state = schedule(row["repetitions"], row["interval_days"], row["ease_factor"], rating, at)
        db.execute("UPDATE flashcard_cards SET repetitions = ?, interval_days = ?, ease_factor = ?, "
                   "last_reviewed_at = ?, next_review_at = ? WHERE id = ?",
                   (state["repetitions"], state["interval_days"], state["ease_factor"],
                    at.isoformat(), state["next_review_at"], card_id))
        db.execute("INSERT INTO flashcard_review_events VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (str(uuid4()), card_id, student_id, rating, at.isoformat(),
                    state["next_review_at"], state["interval_days"]))
        return {"card_id": card_id, "rating": rating, "last_reviewed_at": at.isoformat(), **state}


def review_history(student_id: str, card_id: str) -> list[dict]:
    with database() as db:
        owned = db.execute("SELECT 1 FROM flashcard_cards c JOIN flashcard_decks d ON d.id = c.deck_id "
                           "WHERE c.id = ? AND d.student_id = ?", (card_id, student_id)).fetchone()
        if not owned:
            raise CardNotFoundError("Flashcard not found")
        return [dict(row) for row in db.execute("SELECT rating, reviewed_at, next_review_at, interval_days "
                                                "FROM flashcard_review_events WHERE card_id = ? AND student_id = ? "
                                                "ORDER BY reviewed_at DESC, id DESC", (card_id, student_id))]
