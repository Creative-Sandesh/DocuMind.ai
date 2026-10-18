import { useState } from "react";
import type { VocabularyResponse } from "../types/learning";
import { speakText } from "../services/studentApi";
import LearningSources from "./LearningSources";

function VocabularyPractice({ response, token, speechReady, onPractice }: { response: VocabularyResponse; token?: string; speechReady?: boolean; onPractice?: (word: string) => void }) {
  const [revealed, setRevealed] = useState<number[]>([]);
  const [answers, setAnswers] = useState<string[]>(() => response.words.map(() => ""));
  const [speechError, setSpeechError] = useState("");
  return <section className="learning-result" aria-label="Vocabulary practice">
    <div className="learning-result-heading"><div><span className="learning-eyebrow">Word study</span><h3>Vocabulary</h3></div><span>{response.words.length} words</span></div>
    <div className="vocabulary-list">{response.words.map((word, index) => <article className="vocabulary-item" key={`${word.word}-${index}`}>
      <h4>{word.word}</h4>
      {token && <div className="vocabulary-speech-actions"><button type="button" className="secondary-button" disabled={!speechReady} onClick={() => { setSpeechError(""); void speakText(token, word.word).catch((cause) => setSpeechError(cause instanceof Error ? cause.message : "Unable to play word.")); }}>Listen</button><button type="button" className="secondary-button" onClick={() => onPractice?.(word.word)}>Practice speaking</button></div>}
      <p className="vocab-practice-question">{word.practice_question}</p>
      <label className="vocab-response-label">Your answer<textarea value={answers[index]} onChange={(event) => setAnswers((previous) => previous.map((answer, answerIndex) => answerIndex === index ? event.target.value : answer))} placeholder="Try answering before revealing the meaning" /></label>
      <button type="button" className="secondary-button" onClick={() => setRevealed((previous) => previous.includes(index) ? previous.filter((value) => value !== index) : [...previous, index])}>
        {revealed.includes(index) ? "Hide meaning" : "Show meaning"}
      </button>
      {revealed.includes(index) && <div className="vocab-answer">
        <p><strong>Meaning:</strong> {word.definition}</p>
        <p><strong>Nepali:</strong> {word.nepali_meaning}</p>
        <p><strong>Example:</strong> {word.example}</p>
        <LearningSources sources={response.sources} numbers={word.source_numbers} />
      </div>}
    </article>)}</div>{speechError && <p className="panel-error" role="alert">{speechError}</p>}
  </section>;
}

export default VocabularyPractice;
