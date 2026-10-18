import { useEffect, useState } from "react";
import { assignQuiz, publishQuiz, quizResults, updateQuiz } from "../services/teacherApi";
import type { GeneratedQuiz, QuizQuestion, QuestionType } from "../types/learning";
import type { TeacherQuiz, TeacherQuizResult, TeacherStudent, TeacherTopic } from "../types/teacher";

function blankQuestion(type: QuestionType, index: number): QuizQuestion {
  return { type, question: `New question ${index}`, options: type === "multiple_choice" ? ["Option A", "Option B", "Option C", "Option D"] : type === "true_false" ? ["True", "False"] : [],
    correct_answer: type === "short_answer" ? "Example answer" : type === "true_false" ? "True" : "Option A", explanation: "Add an explanation.", difficulty: "beginner", source_numbers: [], rubric_keywords: type === "short_answer" ? ["key idea", "example"] : [] };
}

export default function TeacherQuizEditor({ quiz, topics, students, token, refreshKey, onChanged }: { quiz: TeacherQuiz; topics: TeacherTopic[]; students: TeacherStudent[]; token: string; refreshKey: number; onChanged: () => void }) {
  const [draft, setDraft] = useState<GeneratedQuiz>(quiz.response.quiz);
  const [topicId, setTopicId] = useState(quiz.topic_id ?? "");
  const [selectedStudents, setSelectedStudents] = useState<string[]>([]);
  const [results, setResults] = useState<TeacherQuizResult[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { let active = true; quizResults(token, quiz.id).then((response) => { if (active) setResults(response.results); }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Unable to load results."); }); return () => { active = false; }; }, [quiz.id, token, quiz.status, refreshKey]);

  function changeQuestion(index: number, values: Partial<QuizQuestion>) {
    setDraft((previous) => ({ ...previous, questions: previous.questions.map((question, itemIndex) => itemIndex === index ? { ...question, ...values } : question) }));
  }

  async function run(operation: () => Promise<unknown>, success: string) {
    setBusy(true); setError(""); setMessage("");
    try { await operation(); setMessage(success); onChanged(); const response = await quizResults(token, quiz.id); setResults(response.results); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Quiz action failed."); }
    finally { setBusy(false); }
  }

  const input = { topic_id: topicId || null, quiz: draft };
  return <div className="teacher-quiz-editor">
    <h4>{quiz.status === "draft" ? "Review quiz draft" : "Published quiz"}</h4>
    {quiz.status === "draft" ? <>
      <label>Quiz title<input value={draft.title} onChange={(event) => setDraft((previous) => ({ ...previous, title: event.target.value }))} /></label>
      <label>Course topic<select value={topicId} onChange={(event) => setTopicId(event.target.value)}><option value="">No catalog topic</option>{topics.map((topic) => <option key={topic.id} value={topic.id}>{topic.title}</option>)}</select></label>
      {draft.questions.map((question, index) => <fieldset className="teacher-question" key={index}><legend>Question {index + 1}</legend>
        <label>Type<select value={question.type} onChange={(event) => changeQuestion(index, blankQuestion(event.target.value as QuestionType, index + 1))}><option value="multiple_choice">Multiple choice</option><option value="true_false">True or false</option><option value="short_answer">Short answer</option></select></label>
        <label>Question<textarea value={question.question} onChange={(event) => changeQuestion(index, { question: event.target.value })} /></label>
        {question.type === "multiple_choice" && question.options.map((option, optionIndex) => <label key={optionIndex}>Option {optionIndex + 1}<input value={option} onChange={(event) => { const options = question.options.map((item, itemIndex) => itemIndex === optionIndex ? event.target.value : item); changeQuestion(index, { options, correct_answer: question.correct_answer === option ? event.target.value : question.correct_answer }); }} /></label>)}
        {question.type === "short_answer" ? <><label>Example answer<textarea value={question.correct_answer} onChange={(event) => changeQuestion(index, { correct_answer: event.target.value })} /></label><label>Rubric keywords, comma separated<input value={question.rubric_keywords.join(", ")} onChange={(event) => changeQuestion(index, { rubric_keywords: event.target.value.split(",").map((item) => item.trim()) })} /></label></>
          : <label>Correct answer<select value={question.correct_answer} onChange={(event) => changeQuestion(index, { correct_answer: event.target.value })}>{question.options.map((option) => <option key={option} value={option}>{option}</option>)}</select></label>}
        <label>Explanation<textarea value={question.explanation} onChange={(event) => changeQuestion(index, { explanation: event.target.value })} /></label>
        {draft.questions.length > 1 && <button type="button" className="secondary-button" onClick={() => setDraft((previous) => ({ ...previous, questions: previous.questions.filter((_, itemIndex) => itemIndex !== index) }))}>Remove question</button>}
      </fieldset>)}
      {draft.questions.length < 10 && <button type="button" className="secondary-button" onClick={() => setDraft((previous) => ({ ...previous, questions: [...previous.questions, blankQuestion("multiple_choice", previous.questions.length + 1)] }))}>Add question</button>}
      <div className="teacher-actions"><button className="learning-primary" disabled={busy} onClick={() => void run(() => updateQuiz(token, quiz.id, input), "Draft saved.")}>Save draft</button><button className="secondary-button" disabled={busy} onClick={() => void run(async () => { await updateQuiz(token, quiz.id, input); await publishQuiz(token, quiz.id); }, "Quiz published and locked.")}>Save and publish</button></div>
    </> : <><p>Published questions are locked. Assign this quiz to enrolled students.</p><div className="teacher-student-choices">{students.map((student) => <label key={student.id}><input type="checkbox" checked={selectedStudents.includes(student.id)} onChange={() => setSelectedStudents((previous) => previous.includes(student.id) ? previous.filter((id) => id !== student.id) : [...previous, student.id])} />{student.display_name}</label>)}</div><button className="learning-primary" disabled={busy || students.length === 0} onClick={() => void run(() => assignQuiz(token, quiz.id, selectedStudents), "Quiz assigned. Leave all boxes clear to assign every enrolled student.")}>Assign {selectedStudents.length ? "selected students" : "all students"}</button></>}
    <h4>Assigned results</h4>{results.length ? <div className="table-scroll"><table><thead><tr><th>Student</th><th>Score</th><th>Submitted</th><th>Answers</th></tr></thead><tbody>{results.map((result) => <tr key={result.student_id}><td>{result.display_name}</td><td>{result.score === null ? "Pending" : `${result.score}/${result.max_score}`}</td><td>{result.created_at ? new Date(result.created_at).toLocaleString() : "—"}</td><td>{result.answers.map((answer) => `${answer.question_index + 1}: ${answer.submitted_answer} (${answer.correct ? "correct" : "incorrect"})`).join("; ") || "—"}</td></tr>)}</tbody></table></div> : <p>No students assigned yet.</p>}
    {message && <p className="student-message" role="status">{message}</p>}{error && <p className="panel-error" role="alert">{error}</p>}
  </div>;
}
