import type { Source } from "./chat";

export type Difficulty = "beginner" | "intermediate" | "advanced";
export type Language = "english" | "nepali" | "bilingual";
export type QuestionType = "multiple_choice" | "true_false" | "short_answer";

export interface LearningRequest {
  topic: string;
  difficulty: Difficulty;
  language: Language;
  document_ids: string[];
  lesson_text?: string;
}

export interface LessonSection {
  heading: string;
  explanation: string;
  examples: string[];
}

export interface GeneratedLesson {
  title: string;
  introduction: string;
  sections: LessonSection[];
  key_takeaways: string[];
  practice_questions: string[];
  summary: string;
}

export interface LessonResponse {
  lesson: GeneratedLesson;
  difficulty: Difficulty;
  language: Language;
  sources: Source[];
}

export interface QuizQuestion {
  type: QuestionType;
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  difficulty: Difficulty;
  source_numbers: number[];
  rubric_keywords: string[];
}

export interface GeneratedQuiz {
  title: string;
  questions: QuizQuestion[];
}

export interface QuizResponse {
  quiz: GeneratedQuiz;
  sources: Source[];
  practice_only: boolean;
}

export interface AnswerFeedback {
  question_index: number;
  question_type: QuestionType;
  submitted_answer: string;
  correct_answer: string;
  correct: boolean;
  points: number;
  explanation: string;
  feedback: string;
  provisional: boolean;
}

export interface QuizEvaluationResponse {
  score: number;
  max_score: number;
  results: AnswerFeedback[];
  practice_only: boolean;
}

export interface Flashcard {
  front: string;
  back: string;
  topic: string;
  difficulty: Difficulty;
  source_numbers: number[];
}

export interface FlashcardResponse {
  flashcards: Flashcard[];
  sources: Source[];
}

export interface VocabularyItem {
  word: string;
  definition: string;
  example: string;
  nepali_meaning: string;
  practice_question: string;
  source_numbers: number[];
}

export interface VocabularyResponse {
  words: VocabularyItem[];
  sources: Source[];
}
