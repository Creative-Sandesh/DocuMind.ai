import { useEffect, useState } from "react";
import { createCourse, listCourses, updateCourse } from "../services/teacherApi";
import type { TeacherCourse } from "../types/teacher";
import TeacherCourseWorkspace from "./TeacherCourseWorkspace";

export default function TeacherDashboard({ token }: { token: string }) {
  const [courses, setCourses] = useState<TeacherCourse[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);
  const [loadError, setLoadError] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { let active = true; listCourses(token).then((response) => {
    if (active) { setCourses(response.courses); setSelectedId((previous) => previous && response.courses.some((course) => course.id === previous) ? previous : response.courses[0]?.id ?? null); setLoadError(""); }
  }).catch((cause) => { if (active) setLoadError(cause instanceof Error ? cause.message : "Unable to load courses."); })
    .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token, retryKey]);

  async function saveCourse() {
    setBusy(true); setError(""); setMessage("");
    try {
      const course = editing && selectedId ? await updateCourse(token, selectedId, title, description) : await createCourse(token, title, description);
      const response = await listCourses(token);
      setCourses(response.courses); setSelectedId(course.id); setEditing(false); setTitle(""); setDescription("");
      setMessage(editing ? "Course updated." : "Course created.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save course."); }
    finally { setBusy(false); }
  }

  const selected = courses.find((course) => course.id === selectedId);
  if (loading && courses.length === 0) return <section className="student-panel dashboard-state" role="status"><span className="dashboard-state-icon" aria-hidden="true">◌</span><h2>Loading your courses</h2><p>Opening your teacher workspace.</p></section>;
  if (loadError && courses.length === 0) return <section className="student-panel dashboard-state" role="alert"><span className="dashboard-state-icon" aria-hidden="true">!</span><h2>Courses unavailable</h2><p>{loadError}</p><button type="button" className="secondary-button" onClick={() => { setLoadError(""); setLoading(true); setRetryKey((key) => key + 1); }}>Try again</button></section>;
  return <div className="teacher-dashboard">
    <section className="student-panel student-hero"><h2>Teacher portal</h2><p>Create and manage courses, materials, quizzes, enrollment and progress from actual student records.</p></section>
    <div className="teacher-shell"><aside className="student-panel teacher-course-list"><h3>Your courses</h3>{courses.length ? <div className="teacher-course-buttons">{courses.map((course) => <button key={course.id} type="button" className={course.id === selectedId ? "active" : ""} onClick={() => { setSelectedId(course.id); setEditing(false); }}>{course.title}<small>{course.student_count ?? 0} students</small></button>)}</div> : <p>Create your first course below.</p>}
      <div className="teacher-form"><h4>{editing ? "Edit course" : "New course"}</h4><label>Title<input value={title} maxLength={160} onChange={(event) => setTitle(event.target.value)} /></label><label>Description<textarea value={description} maxLength={2000} onChange={(event) => setDescription(event.target.value)} /></label><div className="teacher-actions"><button className="learning-primary" disabled={busy || !title.trim()} onClick={() => void saveCourse()}>{editing ? "Save course" : "Create course"}</button>{editing && <button className="secondary-button" onClick={() => { setEditing(false); setTitle(""); setDescription(""); }}>Cancel</button>}</div></div>
      {selected && !editing && <button type="button" className="secondary-button" onClick={() => { setEditing(true); setTitle(selected.title); setDescription(selected.description); }}>Edit selected course</button>}
    </aside>
      <div className="teacher-main">{selected ? <><div className="teacher-course-heading"><h3>{selected.title}</h3><p>{selected.description}</p></div><TeacherCourseWorkspace key={selected.id} courseId={selected.id} token={token} /></> : <div className="student-panel"><p>Select or create a course to begin.</p></div>}</div>
    </div>
    {message && <p className="student-message" role="status">{message}</p>}{(error || loadError) && <p className="panel-error" role="alert">{error || loadError}</p>}
  </div>;
}
