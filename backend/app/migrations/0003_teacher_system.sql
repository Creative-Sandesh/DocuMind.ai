ALTER TABLE courses ADD COLUMN teacher_id TEXT REFERENCES users(id);
ALTER TABLE courses ADD COLUMN subject_id TEXT REFERENCES subjects(id);
CREATE INDEX courses_teacher ON courses(teacher_id);
CREATE UNIQUE INDEX courses_subject ON courses(subject_id) WHERE subject_id IS NOT NULL;
CREATE TABLE course_materials (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    document_id TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    uploaded_at TEXT NOT NULL
);
CREATE INDEX course_materials_course ON course_materials(course_id);
CREATE TABLE teacher_quizzes (
    id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    topic_id TEXT REFERENCES topics(id) ON DELETE SET NULL,
    quiz_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX teacher_quizzes_course ON teacher_quizzes(course_id, created_at);
ALTER TABLE practice_quizzes ADD COLUMN teacher_quiz_id TEXT REFERENCES teacher_quizzes(id);
ALTER TABLE study_sessions ADD COLUMN course_id TEXT REFERENCES courses(id);
CREATE TABLE quiz_assignments (
    id TEXT PRIMARY KEY,
    teacher_quiz_id TEXT NOT NULL REFERENCES teacher_quizzes(id) ON DELETE CASCADE,
    student_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    practice_quiz_id TEXT NOT NULL UNIQUE REFERENCES practice_quizzes(id) ON DELETE CASCADE,
    assigned_at TEXT NOT NULL,
    UNIQUE (teacher_quiz_id, student_id)
);
CREATE INDEX quiz_assignments_student ON quiz_assignments(student_id, assigned_at);
