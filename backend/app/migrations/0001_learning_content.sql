CREATE TABLE subjects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL COLLATE NOCASE UNIQUE,
    description TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE topics (
    id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    title TEXT NOT NULL COLLATE NOCASE,
    description TEXT,
    position INTEGER NOT NULL DEFAULT 0 CHECK (position >= 0),
    created_at TEXT NOT NULL,
    UNIQUE (subject_id, title)
);

CREATE INDEX topics_subject_order ON topics(subject_id, position, title);

CREATE TABLE lessons (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    title TEXT NOT NULL COLLATE NOCASE,
    summary TEXT,
    body TEXT,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    position INTEGER NOT NULL DEFAULT 0 CHECK (position >= 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (topic_id, title)
);

CREATE INDEX lessons_topic_order ON lessons(topic_id, position, title);

CREATE TABLE lesson_objectives (
    lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0),
    objective TEXT NOT NULL,
    PRIMARY KEY (lesson_id, position)
);

CREATE TABLE lesson_documents (
    lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    document_id TEXT NOT NULL,
    PRIMARY KEY (lesson_id, document_id)
);
