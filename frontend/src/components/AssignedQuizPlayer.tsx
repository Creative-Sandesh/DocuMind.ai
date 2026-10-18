import { useState } from "react";
import { submitStudentQuiz, type AssignedQuiz } from "../services/studentApi";
import type { QuizEvaluationResponse } from "../types/learning";

export default function AssignedQuizPlayer({ assignment, token, onSaved }: { assignment: AssignedQuiz; token: string; onSaved: () => void }) {
  const [answers, setAnswers] = useState(() => assignment.questions.map(() => ""));
  const [result, setResult] = useState<QuizEvaluationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    setBusy(true); setError("");
    try { const saved = await submitStudentQuiz(token, assignment.practice_quiz_id, answers); setResult(saved.evaluation); onSaved(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to submit quiz."); }
    finally { setBusy(false); }
  }

  return <div className="assigned-player">
    <h4>{assignment.title}</h4><p>{assignment.course_title} · One submission</p>
    {result ? <div role="status"><strong>Score: {result.score}/{result.max_score}</strong>{result.results.map((item) => <p key={item.question_index}>{item.question_index + 1}. {item.feedback}</p>)}</div> : <>
      {assignment.questions.map((question, index) => <fieldset className="quiz-question" key={index}><legend>{index + 1}. {question.question}</legend>
        {question.type === "short_answer" ? <textarea aria-label={`Answer question ${index + 1}`} value={answers[index]} maxLength={2000} onChange={(event) => setAnswers((previous) => previous.map((answer, answerIndex) => answerIndex === index ? event.target.value : answer))} />
          : <div className="quiz-choices">{question.options.map((option) => <label key={option}><input type="radio" name={`assigned-${assignment.id}-${index}`} checked={answers[index] === option} onChange={() => setAnswers((previous) => previous.map((answer, answerIndex) => answerIndex === index ? option : answer))} />{option}</label>)}</div>}
      </fieldset>)}
      <button className="learning-primary" disabled={busy} onClick={() => void submit()}>{busy ? "Submitting..." : "Submit quiz"}</button>
    </>}
    {error && <p className="panel-error" role="alert">{error}</p>}
  </div>;
}
