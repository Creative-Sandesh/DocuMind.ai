import type { TeacherAnalytics } from "../types/teacher";

const duration = (seconds: number) => `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;

export default function TeacherAnalyticsPanel({ data }: { data: TeacherAnalytics }) {
  const summary = data.summary;
  return <div className="teacher-analytics">
    <div className="student-stats"><div><strong>{summary.students}</strong><span>Enrolled students</span></div><div><strong>{summary.completed_assignments}/{summary.assignments}</strong><span>Quizzes completed</span></div><div><strong>{summary.completion_rate_percent === null ? "—" : `${summary.completion_rate_percent}%`}</strong><span>Completion rate</span></div><div><strong>{summary.average_score_percent === null ? "—" : `${summary.average_score_percent}%`}</strong><span>Average score</span></div><div><strong>{duration(summary.study_seconds)}</strong><span>Course study time</span></div></div>
    <h4>Student performance</h4>{data.students.length ? <div className="table-scroll"><table><thead><tr><th>Student</th><th>Lessons</th><th>Quizzes</th><th>Course study time</th></tr></thead><tbody>{data.students.map((student) => <tr key={student.id}><td>{student.display_name}<small>{student.email}</small></td><td>{student.lessons_completed}/{student.total_lessons}</td><td>{student.quizzes_completed}/{student.quizzes_assigned}</td><td>{duration(student.study_seconds)}</td></tr>)}</tbody></table></div> : <p>No enrolled students yet.</p>}
    <h4>Average scores by topic</h4>{data.topics.length ? <div className="teacher-bars">{data.topics.map((topic) => <div key={topic.topic}><div className="teacher-bar-label"><span>{topic.topic}</span><strong>{topic.average_percent}% · {topic.attempts} {topic.attempts === 1 ? "attempt" : "attempts"}</strong></div><div className="teacher-bar-track"><div style={{ width: `${Math.max(0, Math.min(100, topic.average_percent))}%` }} /></div></div>)}</div> : <p>No assigned quiz results yet.</p>}
    <h4>Weak-topic distribution</h4>{data.weak_topic_distribution.length ? <div className="teacher-bars">{data.weak_topic_distribution.map((topic) => <div key={topic.topic}><div className="teacher-bar-label"><span>{topic.topic}</span><strong>{topic.students} {topic.students === 1 ? "student" : "students"}</strong></div><div className="teacher-bar-track weak"><div style={{ width: `${summary.students ? 100 * topic.students / summary.students : 0}%` }} /></div></div>)}</div> : <p>No topic meets the weak-topic rule yet.</p>}
    <p className="teacher-note">{data.weak_topic_rule} {data.study_time_scope}</p>
  </div>;
}
