import { useEffect, useRef, useState } from "react";

import { generateFlashcards, generateLesson, generateQuiz, generateVocabulary } from "../services/learningApi";
import { generatePersonalizedQuiz, generateStudentFlashcards, generateStudentLesson, generateStudentQuiz, generateStudentVocabulary, getSpeechStatus } from "../services/studentApi";
import type { DocumentSummary } from "../types/chat";
import type { PersonalizedQuizPlan, SavedFlashcardDeck, SpeechStatus } from "../types/student";
import type {
  Difficulty, FlashcardResponse, GeneratedQuiz, Language, LearningRequest,
  LessonResponse, QuestionType, QuizEvaluationResponse, QuizResponse, VocabularyResponse,
} from "../types/learning";
import FlashcardStudy from "./FlashcardStudy";
import LessonViewer from "./LessonViewer";
import QuizStudio from "./QuizStudio";
import VocabularyPractice from "./VocabularyPractice";
import SpeechPractice from "./SpeechPractice";

type Tool = "lesson" | "quiz" | "flashcards" | "vocabulary" | "speech";
const TOOLS: { id: Tool; label: string; action: string }[] = [
  { id: "lesson", label: "Lessons", action: "Generate lesson" },
  { id: "quiz", label: "Quizzes", action: "Generate quiz" },
  { id: "flashcards", label: "Flashcards", action: "Generate flashcards" },
  { id: "vocabulary", label: "Vocabulary", action: "Generate vocabulary" },
  { id: "speech", label: "Speech", action: "Practice speech" },
];
const QUESTION_TYPES: { id: QuestionType; label: string }[] = [
  { id: "multiple_choice", label: "Multiple choice" },
  { id: "true_false", label: "True or false" },
  { id: "short_answer", label: "Short answer" },
];

function lessonAsText(response: LessonResponse): string {
  const lesson = response.lesson;
  return [lesson.title, lesson.introduction,
    ...lesson.sections.flatMap((section) => [section.heading, section.explanation, ...section.examples]),
    ...lesson.key_takeaways, lesson.summary].join("\n").slice(0, 12000);
}

function LearningTools({ documents, studentToken, onAttemptSaved, practicePlan }: { documents: DocumentSummary[]; studentToken?: string; onAttemptSaved?: () => void; practicePlan?: { topic: string; sequence: number; personalizedKey?: string } | null }) {
  const [tool, setTool] = useState<Tool>(practicePlan ? "quiz" : "lesson");
  const [topic, setTopic] = useState(practicePlan?.topic ?? "");
  const [difficulty, setDifficulty] = useState<Difficulty>(practicePlan ? "intermediate" : "beginner");
  const [adaptive, setAdaptive] = useState(Boolean(practicePlan));
  const [personalizedKey, setPersonalizedKey] = useState(practicePlan?.personalizedKey);
  const [adaptiveMessage, setAdaptiveMessage] = useState("");
  const [language, setLanguage] = useState<Language>("english");
  const [sourceIds, setSourceIds] = useState<string[]>([]);
  const [count, setCount] = useState(5);
  const [questionTypes, setQuestionTypes] = useState<QuestionType[]>(["multiple_choice"]);
  const [lesson, setLesson] = useState<LessonResponse | null>(null);
  const [lessonKey, setLessonKey] = useState("");
  const [quiz, setQuiz] = useState<QuizResponse | null>(null);
  const [savedQuizId, setSavedQuizId] = useState<string | undefined>();
  const [quizVersion, setQuizVersion] = useState(0);
  const [quizTopic, setQuizTopic] = useState("");
  const [personalizedPlan, setPersonalizedPlan] = useState<PersonalizedQuizPlan | null>(null);
  const [flashcards, setFlashcards] = useState<FlashcardResponse | null>(null);
  const [savedDeck, setSavedDeck] = useState<SavedFlashcardDeck | null>(null);
  const [flashcardVersion, setFlashcardVersion] = useState(0);
  const [vocabulary, setVocabulary] = useState<VocabularyResponse | null>(null);
  const [vocabularyVersion, setVocabularyVersion] = useState(0);
  const [lastMistakes, setLastMistakes] = useState<string[]>([]);
  const [lastQuizTopic, setLastQuizTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [speechStatus, setSpeechStatus] = useState<SpeechStatus | null>(null);
  const [speechText, setSpeechText] = useState("");
  const inFlight = useRef(false);
  const availableSourceIds = sourceIds.filter((id) => documents.some((document) => document.document_id === id));
  const settingsKey = [topic.trim().toLocaleLowerCase(), difficulty, language, [...availableSourceIds].sort().join(",")].join("|");

  useEffect(() => {
    if (!studentToken) return;
    let active = true;
    getSpeechStatus(studentToken).then((status) => { if (active) setSpeechStatus(status); })
      .catch(() => { if (active) setSpeechStatus(null); });
    return () => { active = false; };
  }, [studentToken]);

  function toggleSource(id: string) {
    setSourceIds((previous) => {
      const available = previous.filter((item) => documents.some((document) => document.document_id === item));
      return available.includes(id) ? available.filter((item) => item !== id)
        : available.length < 5 ? [...available, id] : available;
    });
  }

  function toggleQuestionType(id: QuestionType) {
    setQuestionTypes((previous) => previous.includes(id) ? previous.filter((item) => item !== id) : [...previous, id]);
  }

  function handleEvaluated(generated: GeneratedQuiz, result: QuizEvaluationResponse) {
    setLastMistakes(result.results.filter((item) => !item.correct).map((item) => generated.questions[item.question_index].question));
    setLastQuizTopic(quizTopic);
    if (savedQuizId) onAttemptSaved?.();
  }

  async function handleGenerate() {
    if (tool === "speech") return;
    const cleanTopic = topic.trim();
    if (!cleanTopic) { setError("Enter a topic first."); return; }
    if (tool === "quiz" && questionTypes.length === 0) { setError("Select at least one question type."); return; }
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError("");
    const request: LearningRequest = {
      topic: cleanTopic, difficulty, language, document_ids: availableSourceIds,
      ...(lesson && lessonKey === settingsKey ? { lesson_text: lessonAsText(lesson) } : {}),
    };
    try {
      if (tool === "lesson") {
        const generated = studentToken ? await generateStudentLesson(studentToken, request) : await generateLesson(request);
        setLesson(generated);
        setLessonKey(settingsKey);
      } else if (tool === "quiz") {
        const quizRequest = { ...request, question_count: Math.min(count, 10), question_types: questionTypes, adaptive };
        if (studentToken) {
          const saved = await generateStudentQuiz(studentToken, quizRequest);
          setQuiz(saved.response); setSavedQuizId(saved.quiz_id);
          setAdaptiveMessage(saved.adaptive_decision ? `Used ${saved.adaptive_decision.effective_difficulty} difficulty. ${saved.adaptive_decision.reason}` : "");
        } else {
          setQuiz(await generateQuiz(quizRequest)); setSavedQuizId(undefined); setAdaptiveMessage("");
        }
        setQuizTopic(cleanTopic.toLocaleLowerCase());
        setPersonalizedPlan(null);
        setQuizVersion((version) => version + 1);
      } else if (tool === "flashcards") {
        const flashcardRequest = { ...request, count, mistakes: lastQuizTopic === cleanTopic.toLocaleLowerCase() ? lastMistakes : [] };
        if (studentToken) {
          const generated = await generateStudentFlashcards(studentToken, flashcardRequest);
          setFlashcards(generated); setSavedDeck(generated);
        } else { setFlashcards(await generateFlashcards(flashcardRequest)); setSavedDeck(null); }
        setFlashcardVersion((version) => version + 1);
      } else {
        const generated = studentToken ? await generateStudentVocabulary(studentToken, { ...request, count }) : await generateVocabulary({ ...request, count });
        setVocabulary(generated);
        setVocabularyVersion((version) => version + 1);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Unable to generate learning content.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  async function handlePersonalized() {
    if (!studentToken || inFlight.current) return;
    inFlight.current = true; setBusy(true); setError("");
    try {
      const saved = await generatePersonalizedQuiz(studentToken, {
        ...(personalizedKey ? { topic_key: personalizedKey } : {}),
        question_count: Math.min(count, 10), language,
      });
      setTool("quiz"); setTopic(saved.plan.topic); setPersonalizedKey(undefined); setDifficulty(saved.plan.difficulty);
      setQuiz(saved.response); setSavedQuizId(saved.quiz_id); setPersonalizedPlan(saved.plan);
      setQuizTopic(saved.plan.topic.toLocaleLowerCase()); setQuizVersion((version) => version + 1);
      setAdaptiveMessage("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to generate a personalized quiz."); }
    finally { inFlight.current = false; setBusy(false); }
  }

  const selectedTool = TOOLS.find((item) => item.id === tool)!;
  return <section className="learning-tools" aria-label="AI learning tools">
    <div className="learning-hero"><span className="learning-eyebrow">Local AI tutor</span><h2>Learn, practice, and review</h2>
      <p>Create lessons and study materials on your computer. Choose uploaded documents to ground the generated content in your own material.</p></div>

    <div className="learning-tabs" role="group" aria-label="Learning tool">
      {TOOLS.filter((item) => item.id !== "speech" || studentToken).map((item) => <button key={item.id} type="button" className={tool === item.id ? "active" : ""} aria-pressed={tool === item.id} onClick={() => { setTool(item.id); setError(""); }}>{item.label}</button>)}
    </div>

    <div className="learning-layout">
      <div className="learning-config">
        <h3>Study settings</h3>
        <label htmlFor="learning-topic">Topic</label>
        <input id="learning-topic" value={topic} maxLength={160} placeholder="For example, Python loops" onChange={(event) => { setTopic(event.target.value); setPersonalizedKey(undefined); setAdaptiveMessage(""); }} />
        <div className="learning-fields">
          <div><label htmlFor="learning-difficulty">Difficulty</label><select id="learning-difficulty" value={difficulty} onChange={(event) => { setDifficulty(event.target.value as Difficulty); setAdaptiveMessage(""); }}><option value="beginner">Beginner</option><option value="intermediate">Intermediate</option><option value="advanced">Advanced</option></select></div>
          <div><label htmlFor="learning-language">Language</label><select id="learning-language" value={language} onChange={(event) => setLanguage(event.target.value as Language)}><option value="english">English</option><option value="nepali">Nepali</option><option value="bilingual">English + Nepali</option></select></div>
        </div>

        <fieldset className="learning-document-choice"><legend>Use uploaded documents (optional)</legend>
          {documents.length === 0 ? <p>Upload a document in Document chat to use your own material here.</p> : documents.map((document) => <label key={document.document_id}>
            <input type="checkbox" checked={availableSourceIds.includes(document.document_id)} disabled={!availableSourceIds.includes(document.document_id) && availableSourceIds.length >= 5} onChange={() => toggleSource(document.document_id)} />{document.filename}
          </label>)}
          <small>Up to five documents. Generation stops when selected material has no relevant evidence.</small>
        </fieldset>

        {tool !== "lesson" && tool !== "speech" && <div><label htmlFor="learning-count">{tool === "quiz" ? "Questions" : tool === "flashcards" ? "Cards" : "Words"}</label><input id="learning-count" type="number" min={1} max={tool === "quiz" ? 10 : 12} value={Math.min(count, tool === "quiz" ? 10 : 12)} onChange={(event) => setCount(Math.max(1, Math.min(12, Number(event.target.value) || 1)))} /></div>}
        {tool === "quiz" && <fieldset className="learning-question-types"><legend>Question types</legend>{QUESTION_TYPES.map((item) => <label key={item.id}><input type="checkbox" checked={questionTypes.includes(item.id)} onChange={() => toggleQuestionType(item.id)} />{item.label}</label>)}</fieldset>}
        {tool === "quiz" && studentToken && <label className="adaptive-choice"><input type="checkbox" checked={adaptive} onChange={(event) => { setAdaptive(event.target.checked); setAdaptiveMessage(""); }} /> Adjust quiz difficulty from my saved answers</label>}
        {tool === "quiz" && adaptiveMessage && <p className="learning-hint" role="status">{adaptiveMessage}</p>}
        {tool === "quiz" && studentToken && <button type="button" className="secondary-button" disabled={busy} onClick={() => void handlePersonalized()}>Generate personalized quiz{personalizedKey ? " for recommended topic" : ""}</button>}
        {tool === "speech" && <p className="learning-hint">Use locally installed speech models. The microphone and audio stay on this device and its backend.</p>}
        {tool !== "lesson" && lesson && lessonKey === settingsKey && <p className="learning-hint">Your generated lesson will be used as study context.</p>}
        {tool === "flashcards" && lastMistakes.length > 0 && lastQuizTopic === topic.trim().toLocaleLowerCase() && <p className="learning-hint">Cards will focus on {lastMistakes.length} recent quiz {lastMistakes.length === 1 ? "mistake" : "mistakes"}.</p>}
        {tool !== "speech" && <button type="button" className="learning-primary" disabled={busy || !topic.trim() || (tool === "quiz" && questionTypes.length === 0)} onClick={() => void handleGenerate()}>
          {busy && <span className="button-spinner" aria-hidden="true" />}{busy ? "Generating with local Ollama..." : selectedTool.action}
        </button>}
        {busy && <p className="learning-progress" role="status">Building {tool === "flashcards" ? "flashcards" : tool === "vocabulary" ? "vocabulary" : `a ${tool}`} {availableSourceIds.length ? `from ${availableSourceIds.length} selected ${availableSourceIds.length === 1 ? "document" : "documents"}` : "from your topic"}. This can take a moment.</p>}
        {!busy && !topic.trim() && tool !== "speech" && <p className="learning-hint">Enter a topic above to get started.</p>}
        {tool === "quiz" && questionTypes.length === 0 && <p className="learning-hint">Choose at least one question type.</p>}
        {error && <p className="panel-error" role="alert">{error}</p>}
      </div>

      <div className="learning-output" aria-live="polite">
        <div hidden={tool !== "lesson"}>{lesson ? <LessonViewer response={lesson} /> : <p className="learning-empty">Enter a topic to create a lesson with examples and practice questions.</p>}</div>
        <div hidden={tool !== "quiz"}>{personalizedPlan && <div className="personalized-summary"><strong>Personalized focus: {personalizedPlan.topic}</strong><p>{personalizedPlan.reason} Difficulty: {personalizedPlan.difficulty}.</p>{personalizedPlan.prior_errors.length > 0 && <small>Uses {personalizedPlan.prior_errors.length} saved mistake(s) as concept cues.</small>}</div>}{quiz ? <QuizStudio key={quizVersion} response={quiz} onEvaluated={handleEvaluated} savedQuizId={savedQuizId} studentToken={studentToken} /> : <p className="learning-empty">Generate a quiz, then practice or review the draft questions.</p>}</div>
        <div hidden={tool !== "flashcards"}>{flashcards ? <FlashcardStudy key={flashcardVersion} response={flashcards} cardIds={savedDeck?.card_ids} token={studentToken} onReviewed={onAttemptSaved} /> : <p className="learning-empty">Generate study cards from a topic, lesson, document, or quiz mistakes.</p>}</div>
        <div hidden={tool !== "vocabulary"}>{vocabulary ? <VocabularyPractice key={vocabularyVersion} response={vocabulary} token={studentToken} speechReady={Boolean(speechStatus?.text_to_speech)} onPractice={(word) => { setSpeechText(word); setTool("speech"); }} /> : <p className="learning-empty">Generate vocabulary with definitions, examples, Nepali meanings, and practice prompts.</p>}</div>
        {tool === "speech" && studentToken && <SpeechPractice token={studentToken} status={speechStatus} text={speechText} onTextChange={setSpeechText} />}
      </div>
    </div>
  </section>;
}

export default LearningTools;
