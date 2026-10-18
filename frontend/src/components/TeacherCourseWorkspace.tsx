import { useEffect, useState } from "react";
import {
  courseAnalytics, createQuiz, createTopic, downloadTeacherMaterial, enrollStudent, generateQuiz, listLessons, listMaterials,
  listQuizzes, listStudents, listTopics, removeMaterial, removeStudent, saveLesson, updateMaterial, uploadMaterial,
} from "../services/teacherApi";
import type { Difficulty, Language, QuestionType } from "../types/learning";
import type { TeacherAnalytics, TeacherLesson, TeacherMaterial, TeacherQuiz, TeacherStudent, TeacherTopic } from "../types/teacher";
import TeacherAnalyticsPanel from "./TeacherAnalyticsPanel";
import TeacherQuizEditor from "./TeacherQuizEditor";

type Tab = "content" | "materials" | "quizzes" | "students" | "analytics";
const TABS: { id: Tab; label: string }[] = [{ id: "content", label: "Topics & lessons" }, { id: "materials", label: "Materials" }, { id: "quizzes", label: "Quizzes" }, { id: "students", label: "Students" }, { id: "analytics", label: "Analytics" }];

export default function TeacherCourseWorkspace({ courseId, token }: { courseId: string; token: string }) {
  const [tab, setTab] = useState<Tab>("content");
  const [topics, setTopics] = useState<TeacherTopic[]>([]);
  const [lessons, setLessons] = useState<TeacherLesson[]>([]);
  const [materials, setMaterials] = useState<TeacherMaterial[]>([]);
  const [quizzes, setQuizzes] = useState<TeacherQuiz[]>([]);
  const [students, setStudents] = useState<TeacherStudent[]>([]);
  const [analytics, setAnalytics] = useState<TeacherAnalytics | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [topicTitle, setTopicTitle] = useState("");
  const [topicDescription, setTopicDescription] = useState("");
  const [topicPosition, setTopicPosition] = useState(0);
  const [editingLessonId, setEditingLessonId] = useState<string | null>(null);
  const [lessonTopicId, setLessonTopicId] = useState("");
  const [lessonTitle, setLessonTitle] = useState("");
  const [lessonSummary, setLessonSummary] = useState("");
  const [lessonBody, setLessonBody] = useState("");
  const [lessonDifficulty, setLessonDifficulty] = useState<Difficulty>("beginner");
  const [lessonPosition, setLessonPosition] = useState(0);
  const [lessonObjectives, setLessonObjectives] = useState("");
  const [lessonDocuments, setLessonDocuments] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [editingMaterialId, setEditingMaterialId] = useState<string | null>(null);
  const [materialTitle, setMaterialTitle] = useState("");
  const [materialDescription, setMaterialDescription] = useState("");
  const [studentEmail, setStudentEmail] = useState("");
  const [selectedQuizId, setSelectedQuizId] = useState<string | null>(null);
  const [quizTopicId, setQuizTopicId] = useState("");
  const [quizPromptTopic, setQuizPromptTopic] = useState("");
  const [quizDifficulty, setQuizDifficulty] = useState<Difficulty>("beginner");
  const [quizLanguage, setQuizLanguage] = useState<Language>("english");
  const [quizCount, setQuizCount] = useState(5);
  const [quizTypes, setQuizTypes] = useState<QuestionType[]>(["multiple_choice"]);
  const [quizDocuments, setQuizDocuments] = useState<string[]>([]);

  useEffect(() => {
    let active = true;
    Promise.all([listTopics(token, courseId), listLessons(token, courseId), listMaterials(token, courseId), listQuizzes(token, courseId), listStudents(token, courseId), courseAnalytics(token, courseId)])
      .then(([topicData, lessonData, materialData, quizData, studentData, analyticsData]) => {
        if (!active) return;
        setTopics(topicData.topics); setLessons(lessonData.lessons); setMaterials(materialData.materials);
        setQuizzes(quizData.quizzes); setStudents(studentData.students); setAnalytics(analyticsData); setError("");
      }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Unable to load course."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [courseId, token, refreshKey]);

  async function run<T>(operation: () => Promise<T>, success: string, after?: (result: T) => void) {
    setBusy(true); setError(""); setMessage("");
    try { const result = await operation(); after?.(result); setRefreshKey((value) => value + 1); setMessage(success); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Action failed."); }
    finally { setBusy(false); }
  }

  function editLesson(lesson: TeacherLesson) {
    setEditingLessonId(lesson.id); setLessonTopicId(lesson.topic_id); setLessonTitle(lesson.title);
    setLessonSummary(lesson.summary ?? ""); setLessonBody(lesson.body ?? ""); setLessonDifficulty(lesson.difficulty);
    setLessonPosition(lesson.position); setLessonObjectives(lesson.objectives.join("\n")); setLessonDocuments(lesson.source_document_ids);
  }

  function clearLesson() {
    setEditingLessonId(null); setLessonTitle(""); setLessonSummary(""); setLessonBody("");
    setLessonObjectives(""); setLessonDocuments([]); setLessonPosition(0);
  }

  function toggleDocument(id: string, selected: string[], setSelected: (value: string[]) => void) {
    setSelected(selected.includes(id) ? selected.filter((item) => item !== id) : selected.length < 5 ? [...selected, id] : selected);
  }

  const selectedQuiz = quizzes.find((quiz) => quiz.id === selectedQuizId);
  return <div className="teacher-workspace">
    <div className="teacher-tabs" role="group" aria-label="Course tools">{TABS.map((item) => <button key={item.id} type="button" className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)}>{item.label}</button>)}<button type="button" onClick={() => setRefreshKey((value) => value + 1)}>Refresh data</button></div>
    {loading && <p role="status">Loading course...</p>}
    {tab === "content" && <div className="teacher-grid">
      <section className="student-panel"><h3>Topics</h3><ul>{topics.map((topic) => <li key={topic.id}>{topic.position + 1}. {topic.title}</li>)}</ul>
        <div className="teacher-form"><label>Topic title<input value={topicTitle} maxLength={160} onChange={(event) => setTopicTitle(event.target.value)} /></label><label>Description<textarea value={topicDescription} maxLength={2000} onChange={(event) => setTopicDescription(event.target.value)} /></label><label>Order<input type="number" min={0} value={topicPosition} onChange={(event) => setTopicPosition(Number(event.target.value) || 0)} /></label><button className="learning-primary" disabled={busy || !topicTitle.trim()} onClick={() => void run(() => createTopic(token, courseId, topicTitle, topicDescription, topicPosition), "Topic created.", () => { setTopicTitle(""); setTopicDescription(""); })}>Add topic</button></div>
      </section>
      <section className="student-panel"><h3>Lessons</h3>{lessons.length ? <ul>{lessons.map((lesson) => <li key={lesson.id}><button type="button" className="teacher-link-button" onClick={() => editLesson(lesson)}>{lesson.title}</button> · {lesson.difficulty}</li>)}</ul> : <p>Add a topic, then create a lesson.</p>}
        <div className="teacher-form"><h4>{editingLessonId ? "Edit lesson" : "New lesson"}</h4><label>Topic<select value={lessonTopicId} onChange={(event) => setLessonTopicId(event.target.value)}><option value="">Select topic</option>{topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.title}</option>)}</select></label><label>Title<input value={lessonTitle} maxLength={160} onChange={(event) => setLessonTitle(event.target.value)} /></label><label>Summary<textarea value={lessonSummary} maxLength={2000} onChange={(event) => setLessonSummary(event.target.value)} /></label><label>Lesson body<textarea value={lessonBody} maxLength={100000} onChange={(event) => setLessonBody(event.target.value)} /></label><div className="teacher-form-row"><label>Difficulty<select value={lessonDifficulty} onChange={(event) => setLessonDifficulty(event.target.value as Difficulty)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><label>Order<input type="number" min={0} value={lessonPosition} onChange={(event) => setLessonPosition(Number(event.target.value) || 0)} /></label></div><label>Objectives, one per line<textarea value={lessonObjectives} onChange={(event) => setLessonObjectives(event.target.value)} /></label>
          <fieldset><legend>Source materials</legend>{materials.map((material) => <label key={material.id} className="teacher-check"><input type="checkbox" checked={lessonDocuments.includes(material.document_id)} onChange={() => toggleDocument(material.document_id, lessonDocuments, setLessonDocuments)} />{material.title}</label>)}</fieldset>
          <div className="teacher-actions"><button className="learning-primary" disabled={busy || !lessonTopicId || !lessonTitle.trim()} onClick={() => void run(() => saveLesson(token, courseId, { topic_id: lessonTopicId, title: lessonTitle, summary: lessonSummary, body: lessonBody, difficulty: lessonDifficulty, position: lessonPosition, objectives: lessonObjectives.split("\n").map((item) => item.trim()).filter(Boolean), source_document_ids: lessonDocuments }, editingLessonId ?? undefined), editingLessonId ? "Lesson updated." : "Lesson created.", clearLesson)}>{editingLessonId ? "Save lesson" : "Add lesson"}</button>{editingLessonId && <button type="button" className="secondary-button" onClick={clearLesson}>Cancel edit</button>}</div>
        </div>
      </section>
    </div>}
    {tab === "materials" && <div className="teacher-grid"><section className="student-panel"><h3>Upload course material</h3><p>PDF or TXT, up to 100 MB. The existing local document pipeline indexes the file.</p><input type="file" accept=".pdf,.txt,application/pdf,text/plain" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /><button className="learning-primary" disabled={busy || !file} onClick={() => { if (file) void run(() => uploadMaterial(token, courseId, file), "Material uploaded.", () => setFile(null)); }}>Upload</button></section><section className="student-panel"><h3>Course materials</h3>{materials.length ? <ul>{materials.map((material) => <li key={material.id}><strong>{material.title}</strong> <small>{material.filename}</small><div className="teacher-actions"><button type="button" className="secondary-button" disabled={busy} onClick={() => void run(() => downloadTeacherMaterial(token, courseId, material.id, material.filename), "Download started.")}>Download</button><button type="button" className="secondary-button" onClick={() => { setEditingMaterialId(material.id); setMaterialTitle(material.title); setMaterialDescription(material.description); }}>Edit metadata</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void run(() => removeMaterial(token, courseId, material.id), "Material removed.")}>Remove</button></div></li>)}</ul> : <p>No materials uploaded yet.</p>}{editingMaterialId && <div className="teacher-form"><h4>Edit material</h4><label>Title<input value={materialTitle} onChange={(event) => setMaterialTitle(event.target.value)} /></label><label>Description<textarea value={materialDescription} onChange={(event) => setMaterialDescription(event.target.value)} /></label><button className="learning-primary" disabled={busy || !materialTitle.trim()} onClick={() => void run(() => updateMaterial(token, courseId, editingMaterialId, materialTitle, materialDescription), "Material updated.", () => setEditingMaterialId(null))}>Save metadata</button></div>}</section></div>}
    {tab === "students" && <div className="teacher-grid"><section className="student-panel"><h3>Enroll student</h3><p>Students create their own accounts. Enter the account email to enroll them.</p><div className="teacher-form"><label>Student email<input type="email" value={studentEmail} onChange={(event) => setStudentEmail(event.target.value)} /></label><button className="learning-primary" disabled={busy || !studentEmail.trim()} onClick={() => void run(() => enrollStudent(token, courseId, studentEmail), "Student enrolled.", () => setStudentEmail(""))}>Enroll</button></div></section><section className="student-panel"><h3>Enrolled students</h3>{students.length ? <ul>{students.map((student) => <li key={student.id}>{student.display_name} · {student.email}<button type="button" className="secondary-button" disabled={busy} onClick={() => void run(() => removeStudent(token, courseId, student.id), "Student removed from course.")}>Remove</button></li>)}</ul> : <p>No students enrolled yet.</p>}</section></div>}
    {tab === "quizzes" && <div className="teacher-grid"><section className="student-panel"><h3>Generate quiz draft</h3><div className="teacher-form"><label>Course topic<select value={quizTopicId} onChange={(event) => { setQuizTopicId(event.target.value); const topic = topics.find((item) => item.id === event.target.value); if (topic) setQuizPromptTopic(topic.title); }}><option value="">No catalog topic</option>{topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.title}</option>)}</select></label><label>Quiz topic<input value={quizPromptTopic} maxLength={160} placeholder="For example, Python loops" onChange={(event) => setQuizPromptTopic(event.target.value)} /></label><div className="teacher-form-row"><label>Difficulty<select value={quizDifficulty} onChange={(event) => setQuizDifficulty(event.target.value as Difficulty)}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></label><label>Language<select value={quizLanguage} onChange={(event) => setQuizLanguage(event.target.value as Language)}><option value="english">English</option><option value="nepali">Nepali</option><option value="bilingual">Bilingual</option></select></label><label>Questions<input type="number" min={1} max={10} value={quizCount} onChange={(event) => setQuizCount(Math.max(1, Math.min(10, Number(event.target.value) || 1)))} /></label></div><fieldset><legend>Question types</legend>{(["multiple_choice", "true_false", "short_answer"] as QuestionType[]).map((type) => <label key={type} className="teacher-check"><input type="checkbox" checked={quizTypes.includes(type)} onChange={() => setQuizTypes((previous) => previous.includes(type) ? previous.filter((item) => item !== type) : [...previous, type])} />{type.replace("_", " ")}</label>)}</fieldset><fieldset><legend>Use course materials (optional)</legend>{materials.map((material) => <label key={material.id} className="teacher-check"><input type="checkbox" checked={quizDocuments.includes(material.document_id)} onChange={() => toggleDocument(material.document_id, quizDocuments, setQuizDocuments)} />{material.title}</label>)}</fieldset><button className="learning-primary" disabled={busy || !quizPromptTopic.trim() || quizTypes.length === 0} onClick={() => void run(() => generateQuiz(token, courseId, { topic_id: quizTopicId || null, topic: quizPromptTopic, difficulty: quizDifficulty, language: quizLanguage, document_ids: quizDocuments, question_count: quizCount, question_types: quizTypes }), "Quiz draft generated. Review it before publishing.", (created) => setSelectedQuizId(created.id))}>Generate with Ollama</button><button type="button" className="secondary-button" disabled={busy} onClick={() => void run(() => createQuiz(token, courseId, { topic_id: quizTopicId || null, quiz: { title: "New quiz", questions: [{ type: "multiple_choice", question: "New question 1", options: ["Option A", "Option B", "Option C", "Option D"], correct_answer: "Option A", explanation: "Add an explanation.", difficulty: "beginner", source_numbers: [], rubric_keywords: [] }] } }), "Blank draft created.", (created) => setSelectedQuizId(created.id))}>Create blank draft</button></div>
        <h3>Saved quizzes</h3>{quizzes.length ? <ul>{quizzes.map((quiz) => <li key={quiz.id}><button type="button" className="teacher-link-button" onClick={() => setSelectedQuizId(quiz.id)}>{quiz.response.quiz.title}</button> · {quiz.status}</li>)}</ul> : <p>No quizzes yet.</p>}</section><section className="student-panel">{selectedQuiz ? <TeacherQuizEditor key={selectedQuiz.id} quiz={selectedQuiz} topics={topics} students={students} token={token} refreshKey={refreshKey} onChanged={() => setRefreshKey((value) => value + 1)} /> : <p>Select a quiz draft to review, edit, publish, assign and see results.</p>}</section></div>}
    {tab === "analytics" && <section className="student-panel"><h3>Course analytics</h3>{analytics ? <TeacherAnalyticsPanel data={analytics} /> : <p>No analytics available yet.</p>}</section>}
    {message && <p className="student-message" role="status">{message}</p>}{error && <p className="panel-error" role="alert">{error}</p>}
  </div>;
}
