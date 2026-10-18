import type { LessonResponse } from "../types/learning";
import LearningSources from "./LearningSources";

function LessonViewer({ response }: { response: LessonResponse }) {
  const { lesson } = response;
  return <article className="learning-result lesson-viewer">
    <div className="learning-result-heading"><div><span className="learning-eyebrow">{response.difficulty} · {response.language}</span><h3>{lesson.title}</h3></div></div>
    <p className="lesson-intro">{lesson.introduction}</p>
    {lesson.sections.map((section, index) => <section key={`${section.heading}-${index}`} className="lesson-section">
      <h4>{section.heading}</h4>
      <p>{section.explanation}</p>
      <div className="lesson-examples"><strong>Examples</strong><ul>{section.examples.map((example, exampleIndex) => <li key={exampleIndex}>{example}</li>)}</ul></div>
    </section>)}
    <section className="lesson-section"><h4>Key takeaways</h4><ul>{lesson.key_takeaways.map((item, index) => <li key={index}>{item}</li>)}</ul></section>
    <section className="lesson-section"><h4>Practice questions</h4><ol>{lesson.practice_questions.map((item, index) => <li key={index}>{item}</li>)}</ol></section>
    <section className="lesson-section"><h4>Summary</h4><p>{lesson.summary}</p></section>
    <LearningSources sources={response.sources} />
  </article>;
}

export default LessonViewer;
