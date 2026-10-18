ALTER TABLE practice_quizzes ADD COLUMN personalized_topic_id TEXT REFERENCES topics(id);
CREATE TABLE flashcard_decks (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    cards_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX flashcard_decks_student ON flashcard_decks(student_id, created_at);
CREATE TABLE flashcard_cards (
    id TEXT PRIMARY KEY,
    deck_id TEXT NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    card_index INTEGER NOT NULL,
    repetitions INTEGER NOT NULL DEFAULT 0,
    interval_days INTEGER NOT NULL DEFAULT 0,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    last_reviewed_at TEXT,
    next_review_at TEXT NOT NULL,
    UNIQUE (deck_id, card_index)
);
CREATE INDEX flashcard_cards_due ON flashcard_cards(next_review_at);
CREATE TABLE flashcard_review_events (
    id TEXT PRIMARY KEY,
    card_id TEXT NOT NULL REFERENCES flashcard_cards(id) ON DELETE CASCADE,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating TEXT NOT NULL CHECK (rating IN ('again', 'hard', 'good', 'easy')),
    reviewed_at TEXT NOT NULL,
    next_review_at TEXT NOT NULL,
    interval_days INTEGER NOT NULL
);
CREATE INDEX flashcard_review_events_student ON flashcard_review_events(student_id, reviewed_at);
