import type { Difficulty, FlashcardResponse, Language, QuizEvaluationResponse, QuizResponse } from "./learning";

export interface StudentUser { id: string; email: string; role: string; display_name: string; preferred_language: Language; learning_goals: string }
export interface StudentSession { token: string; user: StudentUser }
export interface AdaptiveDecision { topic_status: TopicKnowledgeProfile["status"]; selected_difficulty: Difficulty; effective_difficulty: Difficulty; reason: string }
export interface SavedQuiz { quiz_id: string; response: QuizResponse; adaptive_decision: AdaptiveDecision | null }
export interface PersonalizedQuizPlan { topic_key: string; topic: string; topic_id: string | null; status: string; mastery_percent: number | null; difficulty: Difficulty; reason: string; prior_errors: string[]; lesson_objectives: string[] }
export interface PersonalizedSavedQuiz extends SavedQuiz { plan: PersonalizedQuizPlan }
export interface SavedFlashcardDeck extends FlashcardResponse { deck_id: string; card_ids: string[] }
export type ReviewRating = "again" | "hard" | "good" | "easy";
export interface DueCard { id: string; deck_id: string; topic: string; front: string; back: string; difficulty: Difficulty; last_reviewed_at: string | null; next_review_at: string; repetitions: number }
export interface ReviewSummary { due_count: number; total_cards: number }
export interface DueReviews { cards: DueCard[]; summary: ReviewSummary }
export interface LearningRecommendation { type: "review_flashcards" | "attempt_quiz" | "practice_weak_topic" | "revisit_lesson" | "next_lesson"; title: string; reason: string; due_count?: number; topic?: string; topic_key?: string; lesson_id?: string; assignment_id?: string }
export interface SpeechStatus { text_to_speech: boolean; speech_to_text: boolean; language: string; offline_only: boolean; message: string }
export interface Transcription { text: string; language: string; pronunciation_scored: false; note: string }
export interface SavedAttempt { id: string; quiz_id: string; topic: string; created_at: string; evaluation: QuizEvaluationResponse }
export interface StudySession { id: string; started_at: string; ended_at: string | null; duration_seconds: number | null; course_id?: string | null; course_title?: string | null }
export interface TopicKnowledgeProfile {
  topic_key: string; topic_id: string | null; topic: string; attempts: number;
  correct_answers: number; incorrect_answers: number; provisional_answers: number;
  recent_accuracy_percent: number | null; mastery_percent: number | null;
  last_practiced_at: string; evidence: "early" | "supported";
  status: "insufficient_evidence" | "weak" | "developing" | "strong";
  status_reason: string; recommended_difficulty: Difficulty;
}
export interface KnowledgeProfile { topics: TopicKnowledgeProfile[]; recent_window: number; method: string }
export interface StudentDashboard {
  courses: { id: string; title: string; description: string; enrolled_at: string }[]; lessons_completed: { id: string; title: string; completed_at: string }[];
  quiz_attempts: { id: string; quiz_id: string; topic: string; score: number; max_score: number; created_at: string }[];
  total_attempts: number; total_study_seconds: number; study_sessions: StudySession[];
  topic_progress: { topic: string; attempts: number; score: number; max_score: number }[];
  knowledge_profile: KnowledgeProfile;
  review_summary: ReviewSummary;
  recommendations: LearningRecommendation[];
}
export interface CatalogLesson { id: string; title: string; summary: string | null; course_title?: string | null }
export interface StudentLesson extends CatalogLesson { body: string | null; difficulty: string; objectives: string[]; source_document_ids: string[] }
