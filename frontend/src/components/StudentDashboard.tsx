import { useEffect, useState } from "react";
import { completeLesson, downloadStudentMaterial, endStudy, getAssignments, getCatalogLessons, getCourseMaterials, getDashboard, getStudentLesson, startStudy, updateProfile, type AssignedQuiz } from "../services/studentApi";
import type { Language } from "../types/learning";
import type { CatalogLesson, StudentDashboard as DashboardData, StudentLesson, StudentSession } from "../types/student";
import AssignedQuizPlayer from "./AssignedQuizPlayer";
import DueReviewPanel from "./DueReviewPanel";

const formatDate = (date: string) => new Date(date).toLocaleString();
const formatDuration = (seconds: number) => `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m ${seconds % 60}s`;

export default function StudentDashboard({ session, refreshKey, onUserChanged, onPracticeTopic, onPersonalizedQuiz }: { session: StudentSession; refreshKey: number; onUserChanged: (user: StudentSession["user"]) => void; onPracticeTopic: (topic: string) => void; onPersonalizedQuiz: (topicKey?: string) => void }) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [lessons, setLessons] = useState<CatalogLesson[]>([]);
  const [assignments, setAssignments] = useState<AssignedQuiz[]>([]);
  const [materials, setMaterials] = useState<Record<string, { id: string; title: string; description: string; filename: string; document_id: string }[]>>({});
  const [studyCourseId, setStudyCourseId] = useState("");
  const [openAssignmentId, setOpenAssignmentId] = useState<string | null>(null);
  const [openLesson, setOpenLesson] = useState<StudentLesson | null>(null);
  const [name, setName] = useState(session.user.display_name);
  const [language, setLanguage] = useState<Language>(session.user.preferred_language);
  const [goals, setGoals] = useState(session.user.learning_goals);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);

  async function refresh() {
    const [dashboard, catalog, assigned] = await Promise.all([getDashboard(session.token), getCatalogLessons(session.token), getAssignments(session.token)]);
    const courseMaterials = await Promise.all(dashboard.courses.map(async (course) => [course.id, (await getCourseMaterials(session.token, course.id)).materials] as const));
    setData(dashboard); setLessons(catalog.lessons); setAssignments(assigned.assignments); setMaterials(Object.fromEntries(courseMaterials));
  }
  useEffect(() => { let active = true; Promise.all([getDashboard(session.token), getCatalogLessons(session.token), getAssignments(session.token)]).then(async ([dashboard, catalog, assigned]) => {
    const courseMaterials = await Promise.all(dashboard.courses.map(async (course) => [course.id, (await getCourseMaterials(session.token, course.id)).materials] as const));
    if (active) { setData(dashboard); setLessons(catalog.lessons); setAssignments(assigned.assignments); setMaterials(Object.fromEntries(courseMaterials)); setError(""); }
  }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Unable to load dashboard."); })
    .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [session.token, refreshKey, retryKey]);

  async function act(operation: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { await operation(); await refresh(); setMessage(success); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Action failed."); }
    finally { setBusy(false); }
  }

  const active = data?.study_sessions.find((item) => !item.ended_at);
  const completedIds = new Set(data?.lessons_completed.map((item) => item.id) ?? []);
  const nextAssignment = assignments.find((assignment) => !assignment.attempt_id);
  const nextLesson = lessons.find((lesson) => !completedIds.has(lesson.id));
  if (loading && !data) return <section className="student-panel dashboard-state" role="status"><span className="dashboard-state-icon" aria-hidden="true">◌</span><h2>Loading your learning space</h2><p>Gathering courses, lessons, assignments, and progress.</p></section>;
  if (error && !data) return <section className="student-panel dashboard-state" role="alert"><span className="dashboard-state-icon" aria-hidden="true">!</span><h2>Dashboard unavailable</h2><p>{error}</p><button type="button" className="secondary-button" onClick={() => { setError(""); setLoading(true); setRetryKey((key) => key + 1); }}>Try again</button></section>;
  return <div className="student-dashboard">
    <section className="student-panel student-hero"><h2>Welcome, {session.user.display_name}</h2><p>Saved practice and study history for {session.user.email}</p></section>
    <section className="student-panel"><h3>Progress</h3><div className="student-stats"><div><strong>{data?.lessons_completed.length ?? 0}</strong><span>Lessons completed</span></div><div><strong>{data?.total_attempts ?? 0}</strong><span>Quiz attempts</span></div><div><strong>{formatDuration(data?.total_study_seconds ?? 0)}</strong><span>Study time</span></div></div></section>
    <section className="student-panel"><h3>Study session</h3><p>Time is measured by the server from start to finish.</p>
      {active ? <><p>Started {formatDate(active.started_at)}{active.course_title ? ` for ${active.course_title}` : ""}</p><button className="learning-primary" disabled={busy} onClick={() => void act(() => endStudy(session.token, active.id), "Study session saved.")}>End session</button></>
        : <><label className="student-study-choice">Study course<select value={studyCourseId} onChange={(event) => setStudyCourseId(event.target.value)}><option value="">General study</option>{data?.courses.map((course) => <option key={course.id} value={course.id}>{course.title}</option>)}</select></label><button className="learning-primary" disabled={busy} onClick={() => void act(() => startStudy(session.token, studyCourseId || undefined), "Study session started.")}>Start session</button></>}
      <ul>{data?.study_sessions.filter((item) => item.ended_at).slice(0, 5).map((item) => <li key={item.id}>{formatDate(item.started_at)} · {formatDuration(item.duration_seconds ?? 0)}{item.course_title ? ` · ${item.course_title}` : ""}</li>)}</ul>
    </section>
    <section className="student-panel" id="student-assigned-quizzes"><h3>Assigned quizzes</h3>{assignments.length ? <div className="student-assignment-list">{assignments.map((assignment) => <div key={assignment.id}><button type="button" className="secondary-button" onClick={() => setOpenAssignmentId(openAssignmentId === assignment.id ? null : assignment.id)}>{assignment.title} · {assignment.course_title} · {assignment.attempt_id ? "Completed" : "Ready"}</button>{openAssignmentId === assignment.id && (assignment.attempt_id ? <p>Submitted. See your score in Recent quiz scores.</p> : <AssignedQuizPlayer assignment={assignment} token={session.token} onSaved={() => void refresh()} />)}</div>)}</div> : <p>No assigned quizzes yet.</p>}</section>
    <section className="student-panel"><h3>Recent quiz scores</h3>{data?.quiz_attempts.length ? <ul>{data.quiz_attempts.map((item) => <li key={item.id}>{item.topic}: {item.score}/{item.max_score} · {formatDate(item.created_at)}</li>)}</ul> : <p>No saved attempts yet. Generate a quiz in Learning tools while signed in.</p>}</section>
    <section className="student-panel knowledge-panel">
      <div className="knowledge-heading"><div><span className="learning-eyebrow">Based on saved quiz answers</span><h3>Topic knowledge</h3></div><span>{data?.knowledge_profile.topics.length ?? 0} topics</span></div>
      {data?.knowledge_profile.topics.length ? <div className="knowledge-grid">{data.knowledge_profile.topics.map((profile) => <article className="knowledge-topic" key={profile.topic_key}>
        <div className="knowledge-topic-heading"><h4>{profile.topic}</h4><span>{profile.mastery_percent === null ? "No score yet" : `${profile.mastery_percent}%`}</span></div>
        {profile.mastery_percent !== null ? <progress max={100} value={profile.mastery_percent} aria-label={`${profile.topic} mastery estimate`} /> : <p>Only provisional short-answer feedback is available.</p>}
        <p>{profile.correct_answers} correct · {profile.incorrect_answers} incorrect objective answers · {profile.attempts} {profile.attempts === 1 ? "attempt" : "attempts"}</p>
        <div className="knowledge-meta"><span className={profile.evidence === "early" ? "knowledge-evidence early" : "knowledge-evidence"}>{profile.evidence === "early" ? "Early estimate" : "More evidence"}</span><span>Recent: {profile.recent_accuracy_percent === null ? "no objective answers" : `${profile.recent_accuracy_percent}%`}</span></div>
        <p className={`knowledge-status ${profile.status}`}><strong>{profile.status === "insufficient_evidence" ? "Keep gathering evidence" : profile.status === "weak" ? "Needs review" : profile.status === "strong" ? "Ready for a challenge" : "Developing"}</strong> — {profile.status_reason}</p>
        <p>Suggested from intermediate: <strong>{profile.recommended_difficulty}</strong></p>
        {profile.topic_key.startsWith("practice:") && <button type="button" className="secondary-button" onClick={() => onPracticeTopic(profile.topic)}>Practice this topic</button>}
        <small>Last practiced {formatDate(profile.last_practiced_at)}{profile.provisional_answers ? ` · ${profile.provisional_answers} provisional answers excluded` : ""}</small>
      </article>)}</div> : <p>Your topic knowledge appears after your first saved quiz attempt.</p>}
      <details className="knowledge-method"><summary>How this estimate works</summary><p>{data?.knowledge_profile.method}</p></details>
    </section>
    <DueReviewPanel token={session.token} refreshKey={refreshKey} onReviewed={() => void refresh()} />
    <section className="student-panel recommendation-panel">
      <div className="knowledge-heading"><div><span className="learning-eyebrow">Based on your progress</span><h3>Recommended next</h3></div></div>
      {data?.recommendations.length ? <div className="recommendation-grid">{data.recommendations.map((item, index) => <article key={`${item.type}-${item.topic_key ?? item.lesson_id ?? item.assignment_id ?? index}`} className="recommendation-card">
        <h4>{item.title}</h4><p>{item.reason}</p>
        <button type="button" className="secondary-button" onClick={() => {
          if (item.type === "review_flashcards") document.getElementById("student-review")?.scrollIntoView({ block: "start" });
          else if (item.assignment_id) { setOpenAssignmentId(item.assignment_id); document.getElementById("student-assigned-quizzes")?.scrollIntoView({ block: "start" }); }
          else if (item.lesson_id) { void act(async () => setOpenLesson(await getStudentLesson(session.token, item.lesson_id!)), "Lesson opened."); document.getElementById("student-catalog-lessons")?.scrollIntoView({ block: "start" }); }
          else if (item.topic_key) onPersonalizedQuiz(item.topic_key);
          else if (item.topic) onPracticeTopic(item.topic);
        }}>Open activity</button>
      </article>)}</div> : <p>Your next suggestions will appear as you finish lessons, quizzes, or flashcard reviews.</p>}
      <button type="button" className="learning-primary" disabled={!data?.knowledge_profile.topics.length && lessons.length === 0} onClick={() => onPersonalizedQuiz()}>Create a personalized quiz</button>
      {!data?.knowledge_profile.topics.length && lessons.length === 0 && <p>Complete a saved quiz or join a course with lessons to unlock personalized practice.</p>}
    </section>
    <section className="student-panel" id="student-catalog-lessons"><h3>Catalog lessons</h3>{lessons.length ? <ul>{lessons.map((lesson) => <li key={lesson.id}><strong>{lesson.title}</strong>{lesson.course_title ? ` · ${lesson.course_title}` : ""} <button type="button" className="secondary-button" onClick={() => void act(async () => setOpenLesson(await getStudentLesson(session.token, lesson.id)), "Lesson opened.")}>Read lesson</button> {completedIds.has(lesson.id) ? <span>Completed</span> : <button type="button" disabled={busy} onClick={() => void act(() => completeLesson(session.token, lesson.id), "Lesson marked complete.")}>Mark complete</button>}</li>)}</ul> : <p>No catalog lessons have been added yet.</p>}{openLesson && <article className="student-lesson"><h4>{openLesson.title}</h4><p>{openLesson.summary}</p><p>{openLesson.body}</p>{openLesson.objectives.length > 0 && <><strong>Objectives</strong><ul>{openLesson.objectives.map((objective) => <li key={objective}>{objective}</li>)}</ul></>}</article>}</section>
    <section className="student-panel"><h3>Profile</h3><div className="student-fields"><label>Display name<input value={name} maxLength={80} onChange={(event) => setName(event.target.value)} /></label><label>Preferred language<select value={language} onChange={(event) => setLanguage(event.target.value as Language)}><option value="english">English</option><option value="nepali">Nepali</option><option value="bilingual">English + Nepali</option></select></label><label>Learning goals<textarea value={goals} maxLength={1000} onChange={(event) => setGoals(event.target.value)} /></label></div>
      <button className="learning-primary" disabled={busy} onClick={() => void act(async () => { const user = await updateProfile(session.token, { display_name: name, preferred_language: language, learning_goals: goals }); onUserChanged(user); }, "Profile saved.")}>Save profile</button>
    </section>
    <section className="student-panel"><h3>Current courses and materials</h3>{data?.courses.length ? <ul>{data.courses.map((course) => <li key={course.id}><strong>{course.title}</strong>{course.description ? ` — ${course.description}` : ""}{materials[course.id]?.length ? <ul>{materials[course.id].map((material) => <li key={material.id}>{material.title}{material.description ? `: ${material.description}` : ""} <button type="button" className="secondary-button" onClick={() => void act(() => downloadStudentMaterial(session.token, course.id, material.id, material.filename), "Download started.")}>Download</button></li>)}</ul> : <p>No materials assigned yet.</p>}</li>)}</ul> : <p>No enrolled courses yet.</p>}</section>
    <section className="student-panel next-activity"><span className="learning-eyebrow">Keep going</span><h3>Next activity</h3>
      {nextAssignment ? <><p>Complete <strong>{nextAssignment.title}</strong> for {nextAssignment.course_title}.</p><button type="button" className="learning-primary" onClick={() => { setOpenAssignmentId(nextAssignment.id); document.getElementById("student-assigned-quizzes")?.scrollIntoView({ block: "start" }); }}>Open assigned quiz</button></>
        : nextLesson ? <><p>Continue with <strong>{nextLesson.title}</strong>{nextLesson.course_title ? ` in ${nextLesson.course_title}` : ""}.</p><button type="button" className="learning-primary" disabled={busy} onClick={() => { void act(async () => setOpenLesson(await getStudentLesson(session.token, nextLesson.id)), "Lesson opened."); document.getElementById("student-catalog-lessons")?.scrollIntoView({ block: "start" }); }}>Read next lesson</button></>
          : <><p>You're caught up with assigned quizzes and catalog lessons. Create a lesson or quiz on a topic you choose.</p><a className="secondary-button next-activity-link" href="#learning">Open learning tools</a></>}
    </section>
    {message && <p className="student-message" role="status">{message}</p>}{error && <p className="panel-error" role="alert">{error}</p>}
  </div>;
}
