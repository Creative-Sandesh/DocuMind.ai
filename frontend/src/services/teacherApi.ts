import type { LearningRequest, QuestionType } from "../types/learning";
import type { StudentSession } from "../types/student";
import type {
  TeacherAnalytics,
  TeacherCourse,
  TeacherLesson,
  TeacherLessonInput,
  TeacherMaterial,
  TeacherQuiz,
  TeacherQuizInput,
  TeacherQuizResult,
  TeacherStudent,
  TeacherTopic,
} from "../types/teacher";
import { API_BASE_URL } from "./config";

const BASE = `${API_BASE_URL}/teacher`;

async function request<T>(
  path: string,
  method: string,
  token?: string,
  body?: object | FormData,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(body && !(body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
      },
      ...(body
        ? { body: body instanceof FormData ? body : JSON.stringify(body) }
        : {}),
    });
  } catch {
    throw new Error(
      "Cannot reach the backend. Start the backend server and try again.",
    );
  }
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const data: { detail?: string | { msg?: string }[] } =
        await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail))
        message = data.detail
          .map((item) => item.msg ?? "Invalid input")
          .join("; ");
    } catch {
      /* Keep fallback. */
    }
    throw new Error(message);
  }
  return response.status === 204
    ? (undefined as T)
    : (response.json() as Promise<T>);
}

export const registerTeacher = (
  email: string,
  password: string,
  display_name: string,
  teacher_code: string,
) =>
  request<StudentSession>("/register", "POST", undefined, {
    email,
    password,
    display_name,
    teacher_code,
  });
export const listCourses = (token: string) =>
  request<{ courses: TeacherCourse[] }>("/courses", "GET", token);
export const createCourse = (
  token: string,
  title: string,
  description: string,
) => request<TeacherCourse>("/courses", "POST", token, { title, description });
export const updateCourse = (
  token: string,
  id: string,
  title: string,
  description: string,
) =>
  request<TeacherCourse>(`/courses/${id}`, "PUT", token, {
    title,
    description,
  });
export const listTopics = (token: string, courseId: string) =>
  request<{ topics: TeacherTopic[] }>(
    `/courses/${courseId}/topics`,
    "GET",
    token,
  );
export const createTopic = (
  token: string,
  courseId: string,
  title: string,
  description: string,
  position: number,
) =>
  request<TeacherTopic>(`/courses/${courseId}/topics`, "POST", token, {
    title,
    description,
    position,
  });
export const listLessons = (token: string, courseId: string) =>
  request<{ lessons: TeacherLesson[] }>(
    `/courses/${courseId}/lessons`,
    "GET",
    token,
  );
export const saveLesson = (
  token: string,
  courseId: string,
  lesson: TeacherLessonInput,
  lessonId?: string,
) =>
  request<TeacherLesson>(
    `/courses/${courseId}/lessons${lessonId ? `/${lessonId}` : ""}`,
    lessonId ? "PUT" : "POST",
    token,
    lesson,
  );
export const listMaterials = (token: string, courseId: string) =>
  request<{ materials: TeacherMaterial[] }>(
    `/courses/${courseId}/materials`,
    "GET",
    token,
  );
export const uploadMaterial = (token: string, courseId: string, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return request<TeacherMaterial>(
    `/courses/${courseId}/materials`,
    "POST",
    token,
    body,
  );
};
export const updateMaterial = (
  token: string,
  courseId: string,
  materialId: string,
  title: string,
  description: string,
) =>
  request<TeacherMaterial>(
    `/courses/${courseId}/materials/${materialId}`,
    "PUT",
    token,
    { title, description },
  );
export const removeMaterial = (
  token: string,
  courseId: string,
  materialId: string,
) =>
  request<void>(
    `/courses/${courseId}/materials/${materialId}`,
    "DELETE",
    token,
  );
export const listStudents = (token: string, courseId: string) =>
  request<{ students: TeacherStudent[] }>(
    `/courses/${courseId}/students`,
    "GET",
    token,
  );
export const enrollStudent = (token: string, courseId: string, email: string) =>
  request<TeacherStudent>(`/courses/${courseId}/students`, "POST", token, {
    email,
  });
export const removeStudent = (
  token: string,
  courseId: string,
  studentId: string,
) =>
  request<void>(`/courses/${courseId}/students/${studentId}`, "DELETE", token);
export const listQuizzes = (token: string, courseId: string) =>
  request<{ quizzes: TeacherQuiz[] }>(
    `/courses/${courseId}/quizzes`,
    "GET",
    token,
  );
export const createQuiz = (
  token: string,
  courseId: string,
  input: TeacherQuizInput,
) => request<TeacherQuiz>(`/courses/${courseId}/quizzes`, "POST", token, input);
export const generateQuiz = (
  token: string,
  courseId: string,
  input: LearningRequest & {
    topic_id: string | null;
    question_count: number;
    question_types: QuestionType[];
  },
) =>
  request<TeacherQuiz>(
    `/courses/${courseId}/quizzes/generate`,
    "POST",
    token,
    input,
  );
export const updateQuiz = (
  token: string,
  quizId: string,
  input: TeacherQuizInput,
) => request<TeacherQuiz>(`/quizzes/${quizId}`, "PUT", token, input);
export const publishQuiz = (token: string, quizId: string) =>
  request<TeacherQuiz>(`/quizzes/${quizId}/publish`, "POST", token);
export const assignQuiz = (
  token: string,
  quizId: string,
  studentIds: string[],
) =>
  request<{ assigned: number; total: number }>(
    `/quizzes/${quizId}/assign`,
    "POST",
    token,
    { student_ids: studentIds },
  );
export const quizResults = (token: string, quizId: string) =>
  request<{ results: TeacherQuizResult[] }>(
    `/quizzes/${quizId}/results`,
    "GET",
    token,
  );
export const courseAnalytics = (token: string, courseId: string) =>
  request<TeacherAnalytics>(`/courses/${courseId}/analytics`, "GET", token);

export async function downloadTeacherMaterial(token: string, courseId: string, materialId: string, filename: string) {
  const response = await fetch(`${BASE}/courses/${courseId}/materials/${materialId}/download`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) throw new Error(response.status === 404 ? "Material file not found." : "Unable to download material.");
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a"); link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
