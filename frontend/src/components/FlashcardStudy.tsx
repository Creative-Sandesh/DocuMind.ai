import { useState } from "react";
import type { FlashcardResponse } from "../types/learning";
import type { ReviewRating } from "../types/student";
import { rateReview } from "../services/studentApi";
import LearningSources from "./LearningSources";

function FlashcardStudy({ response, cardIds, token, onReviewed }: { response: FlashcardResponse; cardIds?: string[]; token?: string; onReviewed?: () => void }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [known, setKnown] = useState<boolean[]>(() => response.flashcards.map(() => false));
  const [rated, setRated] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const card = response.flashcards[index];
  function move(next: number) { setIndex(next); setFlipped(false); }
  async function rate(rating: ReviewRating) {
    const cardId = cardIds?.[index];
    if (!token || !cardId || busy) return;
    setBusy(true); setError("");
    try { const result = await rateReview(token, cardId, rating); setRated((previous) => ({ ...previous, [cardId]: new Date(result.next_review_at).toLocaleString() })); onReviewed?.(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save review."); }
    finally { setBusy(false); }
  }
  return <section className="learning-result" aria-label="Flashcard study">
    <div className="learning-result-heading"><div><span className="learning-eyebrow">Study cards</span><h3>Flashcards</h3></div><span>{cardIds ? `${Object.keys(rated).length}/${cardIds.length} reviewed` : `${known.filter(Boolean).length}/${known.length} known`}</span></div>
    <p>Card {index + 1} of {response.flashcards.length}. Select the card to reveal its answer.</p>
    <button type="button" className="flashcard" onClick={() => setFlipped(!flipped)} aria-label={flipped ? "Show question" : "Reveal answer"}>
      <span>{flipped ? "Answer" : "Question"}</span><strong>{flipped ? card.back : card.front}</strong>
      <small>{flipped ? "Select to show question" : "Select to reveal answer"}</small>
    </button>
    <div className="study-controls">
      <button type="button" onClick={() => move(Math.max(0, index - 1))} disabled={index === 0}>Previous</button>
      {!cardIds && <button type="button" onClick={() => setKnown((previous) => previous.map((value, cardIndex) => cardIndex === index ? !value : value))}>{known[index] ? "Mark for review" : "Mark known"}</button>}
      <button type="button" onClick={() => move(Math.min(response.flashcards.length - 1, index + 1))} disabled={index === response.flashcards.length - 1}>Next</button>
    </div>
    {cardIds && flipped && !rated[cardIds[index]] && <div className="review-ratings">{(["again", "hard", "good", "easy"] as ReviewRating[]).map((rating) => <button key={rating} type="button" className="secondary-button" disabled={busy} onClick={() => void rate(rating)}>{rating}</button>)}</div>}
    {cardIds && rated[cardIds[index]] && <p role="status">Saved. Next review: {rated[cardIds[index]]}.</p>}
    {error && <p className="panel-error" role="alert">{error}</p>}
    <LearningSources sources={response.sources} numbers={card.source_numbers} />
  </section>;
}

export default FlashcardStudy;
