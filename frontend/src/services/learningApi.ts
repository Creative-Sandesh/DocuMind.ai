import type {
  FlashcardResponse, GeneratedQuiz, LearningRequest, LessonResponse,
  QuestionType, QuizEvaluationResponse, QuizResponse, VocabularyResponse,
} from "../types/learning";
import { API_BASE_URL } from "./config";

const BASE_URL = `${API_BASE_URL}/learning`;

async function post<T>(path: string, body: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new Error("Cannot reach the backend. Start the backend server and try again.");
  }
  if (!response.ok) {
    let message = "The learning request failed.";
    try {
      const data: { detail?: string | { msg?: string }[] } = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((item) => item.msg ?? "Invalid input").join("; ");
    } catch { /* Keep the fallback message. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export function generateLesson(request: LearningRequest) {
  return post<LessonResponse>("generate-lesson", request);
}

export function generateQuiz(request: LearningRequest & { question_count: number; question_types: QuestionType[] }) {
  return post<QuizResponse>("generate-quiz", request);
}

export function evaluateQuiz(quiz: GeneratedQuiz, answers: string[]) {
  return post<QuizEvaluationResponse>("evaluate-quiz", {
    quiz,
    answers: answers.map((answer, question_index) => ({ question_index, answer })),
  });
}

export function generateFlashcards(request: LearningRequest & { count: number; mistakes: string[] }) {
  return post<FlashcardResponse>("generate-flashcards", request);
}

export function generateVocabulary(request: LearningRequest & { count: number }) {
  return post<VocabularyResponse>("generate-vocabulary", request);
}
