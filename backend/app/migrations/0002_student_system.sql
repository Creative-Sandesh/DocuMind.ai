CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'teacher')),
    created_at TEXT NOT NULL
);
CREATE TABLE student_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    display_name TEXT NOT NULL,
    preferred_language TEXT NOT NULL DEFAULT 'english' CHECK (preferred_language IN ('english', 'nepali', 'bilingual')),
    learning_goals TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX auth_sessions_user ON auth_sessions(user_id);
CREATE TABLE courses (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE course_enrollments (
    course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    enrolled_at TEXT NOT NULL,
    PRIMARY KEY (course_id, student_id)
);
CREATE INDEX course_enrollments_student ON course_enrollments(student_id);
CREATE TABLE practice_quizzes (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    quiz_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX practice_quizzes_student ON practice_quizzes(student_id, created_at);
CREATE TABLE quiz_attempts (
    id TEXT PRIMARY KEY,
    quiz_id TEXT NOT NULL REFERENCES practice_quizzes(id) ON DELETE CASCADE,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX quiz_attempts_student ON quiz_attempts(student_id, created_at);
CREATE TABLE attempt_answers (
    attempt_id TEXT NOT NULL REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_index INTEGER NOT NULL,
    submitted_answer TEXT NOT NULL,
    correct INTEGER NOT NULL,
    points INTEGER NOT NULL,
    provisional INTEGER NOT NULL,
    PRIMARY KEY (attempt_id, question_index)
);
CREATE TABLE lesson_progress (
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id TEXT NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    completed_at TEXT NOT NULL,
    PRIMARY KEY (student_id, lesson_id)
);
CREATE TABLE study_sessions (
    id TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds INTEGER
);
CREATE INDEX study_sessions_student ON study_sessions(student_id, started_at);
CREATE UNIQUE INDEX study_sessions_one_active ON study_sessions(student_id) WHERE ended_at IS NULL;
