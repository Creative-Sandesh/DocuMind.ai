import type { LearningRequest, LessonResponse, QuestionType, VocabularyResponse } from "../types/learning";
import type { CatalogLesson, DueReviews, KnowledgeProfile, LearningRecommendation, PersonalizedSavedQuiz, ReviewRating, SavedAttempt, SavedFlashcardDeck, SavedQuiz, SpeechStatus, StudentDashboard, StudentLesson, StudentSession, StudentUser, StudySession, Transcription } from "../types/student";
import { API_BASE_URL } from "./config";

const BASE_URL = API_BASE_URL;

async function request<T>(path: string, method = "GET", body?: object, token?: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method, headers: { ...(body ? { "Content-Type": "application/json" } : {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  } catch { throw new Error("Cannot reach the backend. Start the backend server and try again."); }
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const data: { detail?: string | { msg?: string }[] } = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = data.detail.map((item) => item.msg ?? "Invalid input").join("; ");
    } catch { /* Keep fallback. */ }
    throw new Error(message);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export const register = (email: string, password: string, display_name: string) => request<StudentSession>("/student/register", "POST", { email, password, display_name });
export const login = (email: string, password: string) => request<StudentSession>("/student/login", "POST", { email, password });
export const logout = (token: string) => request<void>("/student/logout", "POST", undefined, token);
export const getMe = (token: string) => request<StudentUser>("/student/me", "GET", undefined, token);
export const updateProfile = (token: string, profile: Pick<StudentUser, "display_name" | "preferred_language" | "learning_goals">) => request<StudentUser>("/student/profile", "PUT", profile, token);
export const getDashboard = (token: string) => request<StudentDashboard>("/student/dashboard", "GET", undefined, token);
export const getKnowledgeProfile = (token: string) => request<KnowledgeProfile>("/student/knowledge-profile", "GET", undefined, token);
export const getCatalogLessons = (token: string) => request<{ lessons: CatalogLesson[] }>("/student/lessons", "GET", undefined, token);
export const getStudentLesson = (token: string, id: string) => request<StudentLesson>(`/student/lessons/${id}`, "GET", undefined, token);
export const completeLesson = (token: string, id: string) => request<{ lesson_id: string }>(`/student/lessons/${id}/complete`, "PUT", undefined, token);
export const startStudy = (token: string, courseId?: string) => request<StudySession>("/student/study-sessions", "POST", courseId ? { course_id: courseId } : {}, token);
export const endStudy = (token: string, id: string) => request<StudySession>(`/student/study-sessions/${id}/end`, "POST", undefined, token);
export const generateStudentQuiz = (token: string, body: LearningRequest & { question_count: number; question_types: QuestionType[]; adaptive?: boolean }) => request<SavedQuiz>("/student/quizzes/generate", "POST", body, token);
export const generatePersonalizedQuiz = (token: string, body: { topic_key?: string; question_count?: number; language?: string }) => request<PersonalizedSavedQuiz>("/student/quizzes/personalized", "POST", body, token);
export const getRecommendations = (token: string) => request<{ recommendations: LearningRecommendation[] }>("/student/recommendations", "GET", undefined, token);
export const getDueReviews = (token: string) => request<DueReviews>("/student/reviews/due", "GET", undefined, token);
export const rateReview = (token: string, cardId: string, rating: ReviewRating) => request<{ card_id: string; rating: ReviewRating; next_review_at: string; interval_days: number }>(`/student/reviews/${cardId}`, "POST", { rating }, token);
export const getReviewHistory = (token: string, cardId: string) => request<{ events: { rating: ReviewRating; reviewed_at: string; next_review_at: string; interval_days: number }[] }>(`/student/reviews/${cardId}/history`, "GET", undefined, token);
export const submitStudentQuiz = (token: string, quizId: string, answers: string[]) => request<SavedAttempt>(`/student/quizzes/${quizId}/attempts`, "POST", { answers: answers.map((answer, question_index) => ({ answer, question_index })) }, token);
export interface AssignedQuiz { id: string; practice_quiz_id: string; course_id: string; course_title: string; assigned_at: string; title: string; attempt_id: string | null; questions: { type: string; question: string; options: string[] }[] }
export const getAssignments = (token: string) => request<{ assignments: AssignedQuiz[] }>("/student/assignments", "GET", undefined, token);
export const getCourseMaterials = (token: string, courseId: string) => request<{ materials: { id: string; title: string; description: string; filename: string; document_id: string }[] }>(`/student/courses/${courseId}/materials`, "GET", undefined, token);
export const generateStudentLesson = (token: string, input: LearningRequest) => request<LessonResponse>("/student/learning/generate-lesson", "POST", input, token);
export const generateStudentFlashcards = (token: string, input: LearningRequest & { count: number; mistakes: string[] }) => request<SavedFlashcardDeck>("/student/learning/generate-flashcards", "POST", input, token);
export const generateStudentVocabulary = (token: string, input: LearningRequest & { count: number }) => request<VocabularyResponse>("/student/learning/generate-vocabulary", "POST", input, token);
export const getSpeechStatus = (token: string) => request<SpeechStatus>("/student/speech/status", "GET", undefined, token);

export async function speakText(token: string, text: string): Promise<void> {
  const response = await fetch(`${BASE_URL}/student/speech/synthesize`, {
    method: "POST", headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: JSON.stringify({ text }),
  });
  if (!response.ok) { const detail = await response.json().catch(() => ({})); throw new Error(detail.detail ?? "Local speech is unavailable."); }
  const url = URL.createObjectURL(await response.blob());
  try { const audio = new Audio(url); await audio.play(); audio.addEventListener("ended", () => URL.revokeObjectURL(url), { once: true }); }
  catch (error) { URL.revokeObjectURL(url); throw error; }
}

export async function transcribeAudio(token: string, audio: Blob): Promise<Transcription> {
  const data = new FormData(); data.append("audio", audio, "recording.wav");
  const response = await fetch(`${BASE_URL}/student/speech/transcribe`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: data });
  if (!response.ok) { const detail = await response.json().catch(() => ({})); throw new Error(detail.detail ?? "Local transcription failed."); }
  return response.json() as Promise<Transcription>;
}

export async function downloadStudentMaterial(token: string, courseId: string, materialId: string, filename: string) {
  const response = await fetch(`${BASE_URL}/student/courses/${courseId}/materials/${materialId}/download`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(response.status === 404 ? "Material file not found." : "Unable to download material.");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a"); link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
