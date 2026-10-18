import type { Difficulty, GeneratedQuiz, QuizResponse } from "./learning";

export interface TeacherCourse { id: string; title: string; description: string; subject_id: string; teacher_id: string; student_count?: number }
export interface TeacherTopic { id: string; subject_id: string; title: string; description: string; position: number }
export interface TeacherLesson { id: string; topic_id: string; title: string; summary: string; body: string; difficulty: Difficulty; position: number; objectives: string[]; source_document_ids: string[] }
export type TeacherLessonInput = Omit<TeacherLesson, "id">;
export interface TeacherMaterial { id: string; course_id: string; document_id: string; filename: string; title: string; description: string; uploaded_at: string }
export interface TeacherStudent { id: string; email: string; display_name: string; enrolled_at: string }
export interface TeacherQuiz { id: string; course_id: string; topic_id: string | null; status: "draft" | "published"; response: QuizResponse; created_at: string; published_at: string | null }
export interface TeacherQuizInput { topic_id: string | null; quiz: GeneratedQuiz }
export interface TeacherQuizResult { student_id: string; email: string; display_name: string; assigned_at: string; attempt_id: string | null; score: number | null; max_score: number | null; created_at: string | null; answers: { question_index: number; submitted_answer: string; correct: number; points: number; provisional: number }[] }
export interface TeacherAnalytics {
  course_id: string;
  summary: { students: number; total_lessons: number; assignments: number; completed_assignments: number; completion_rate_percent: number | null; graded_attempts: number; average_score_percent: number | null; study_seconds: number };
  students: { id: string; email: string; display_name: string; lessons_completed: number; total_lessons: number; quizzes_assigned: number; quizzes_completed: number; study_seconds: number }[];
  topics: { topic: string; attempts: number; score: number; max_score: number; average_percent: number }[];
  weak_topic_distribution: { topic: string; students: number }[];
  weak_topic_rule: string; study_time_scope: string;
}
