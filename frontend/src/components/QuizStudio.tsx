import { useRef, useState } from "react";

import { evaluateQuiz } from "../services/learningApi";
import { submitStudentQuiz } from "../services/studentApi";
import type { GeneratedQuiz, QuizEvaluationResponse, QuizQuestion, QuizResponse } from "../types/learning";
import LearningSources from "./LearningSources";

interface QuizStudioProps {
  response: QuizResponse;
  onEvaluated: (quiz: GeneratedQuiz, result: QuizEvaluationResponse) => void;
  savedQuizId?: string;
  studentToken?: string;
}

function QuizStudio({ response, onEvaluated, savedQuizId, studentToken }: QuizStudioProps) {
  const [quiz, setQuiz] = useState<GeneratedQuiz>(response.quiz);
  const [mode, setMode] = useState<"practice" | "review" | "results">("practice");
  const [answers, setAnswers] = useState<string[]>(() => response.quiz.questions.map(() => ""));
  const [result, setResult] = useState<QuizEvaluationResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);

  function updateQuestion(index: number, update: Partial<QuizQuestion>) {
    setQuiz((previous) => ({ ...previous, questions: previous.questions.map((question, questionIndex) => questionIndex === index ? { ...question, ...update } : question) }));
    setResult(null);
  }

  function updateOption(questionIndex: number, optionIndex: number, value: string) {
    const question = quiz.questions[questionIndex];
    const options = question.options.map((option, index) => index === optionIndex ? value : option);
    updateQuestion(questionIndex, { options, correct_answer: question.correct_answer === question.options[optionIndex] ? value : question.correct_answer });
  }

  async function submit() {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    try {
      const evaluated = savedQuizId && studentToken
        ? (await submitStudentQuiz(studentToken, savedQuizId, answers)).evaluation
        : await evaluateQuiz(quiz, answers);
      setResult(evaluated);
      setMode("results");
      onEvaluated(quiz, evaluated);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to evaluate quiz.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  return <section className="learning-result" aria-label="Quiz practice">
    <div className="learning-result-heading"><div><span className="learning-eyebrow">Practice quiz</span><h3>{quiz.title}</h3></div><span>{quiz.questions.length} questions</span></div>
    <p className="practice-note">{savedQuizId ? "Your attempts are saved to your account. This quiz is locked to keep saved scores consistent." : "Practice only. Generated questions can be reviewed and edited."} Short answers use provisional keyword feedback.</p>
    <div className="study-controls">
      <button type="button" onClick={() => { setMode("practice"); setResult(null); }} disabled={mode === "practice" || busy}>Practice</button>
      {!savedQuizId && <button type="button" onClick={() => setMode("review")} disabled={mode === "review" || busy}>Review and edit draft</button>}
      {result && <button type="button" onClick={() => setMode("results")} disabled={mode === "results"}>Results</button>}
    </div>

    {mode === "review" && <div className="quiz-questions">
      <p>Review the AI draft before using or assigning it. Publishing and assignment arrive with the teacher portal.</p>
      {quiz.questions.map((question, index) => <article className="quiz-question" key={index}>
        <span className="learning-eyebrow">Question {index + 1} · {question.type.replace("_", " ")}</span>
        <label>Question text<textarea value={question.question} onChange={(event) => updateQuestion(index, { question: event.target.value })} /></label>
        {question.type === "multiple_choice" && <div className="quiz-options-editor">{question.options.map((option, optionIndex) => <label key={optionIndex}>Option {optionIndex + 1}<input value={option} onChange={(event) => updateOption(index, optionIndex, event.target.value)} /></label>)}</div>}
        {question.type !== "short_answer" && <label>Correct answer<select value={question.correct_answer} onChange={(event) => updateQuestion(index, { correct_answer: event.target.value })}>{question.options.map((option, optionIndex) => <option key={optionIndex} value={option}>{option}</option>)}</select></label>}
        {question.type === "short_answer" && <>
          <label>Example answer<textarea value={question.correct_answer} onChange={(event) => updateQuestion(index, { correct_answer: event.target.value })} /></label>
          <label>Rubric keywords (comma separated)<input value={question.rubric_keywords.join(", ")} onChange={(event) => updateQuestion(index, { rubric_keywords: event.target.value.split(",").map((item) => item.trim()) })} /></label>
        </>}
        <label>Explanation<textarea value={question.explanation} onChange={(event) => updateQuestion(index, { explanation: event.target.value })} /></label>
        <LearningSources sources={response.sources} numbers={question.source_numbers} />
      </article>)}
    </div>}

    {mode === "practice" && <div className="quiz-questions">
      {quiz.questions.map((question, index) => <fieldset className="quiz-question" key={index}>
        <legend>{index + 1}. {question.question}</legend>
        {question.type === "short_answer" ? <textarea aria-label={`Answer question ${index + 1}`} value={answers[index]} maxLength={2000} onChange={(event) => setAnswers((previous) => previous.map((value, answerIndex) => answerIndex === index ? event.target.value : value))} />
          : <div className="quiz-choices">{question.options.map((option, optionIndex) => <label key={optionIndex}><input type="radio" name={`quiz-question-${index}`} value={option} checked={answers[index] === option} onChange={() => setAnswers((previous) => previous.map((value, answerIndex) => answerIndex === index ? option : value))} />{option}</label>)}</div>}
      </fieldset>)}
      <button type="button" className="learning-primary" disabled={busy} onClick={() => void submit()}>{busy ? "Checking answers..." : "Check answers"}</button>
    </div>}

    {mode === "results" && result && <div className="quiz-results" role="status">
      <h4>Score: {result.score}/{result.max_score}</h4>
      <p>Practice result only. Short-answer marks are provisional and based on the listed rubric keywords.</p>
      {result.results.map((item) => <article className="quiz-feedback" key={item.question_index}>
        <strong>{item.question_index + 1}. {quiz.questions[item.question_index].question}</strong>
        <p>{item.correct ? "✓" : "✕"} {item.feedback}</p>
        <p><strong>Explanation:</strong> {item.explanation}</p>
        <LearningSources sources={response.sources} numbers={quiz.questions[item.question_index].source_numbers} />
      </article>)}
      <button type="button" className="secondary-button" onClick={() => { setAnswers(quiz.questions.map(() => "")); setResult(null); setMode("practice"); }}>Try again</button>
    </div>}
    {error && <p className="panel-error" role="alert">{error}</p>}
  </section>;
}

export default QuizStudio;
