import { useEffect, useState } from "react";
import { getDueReviews, getReviewHistory, rateReview } from "../services/studentApi";
import type { DueReviews, ReviewRating } from "../types/student";

const RATINGS: { id: ReviewRating; label: string }[] = [
  { id: "again", label: "Again · 10 min" }, { id: "hard", label: "Hard" },
  { id: "good", label: "Good" }, { id: "easy", label: "Easy" },
];

export default function DueReviewPanel({ token, refreshKey, onReviewed }: { token: string; refreshKey: number; onReviewed: () => void }) {
  const [queue, setQueue] = useState<DueReviews | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [history, setHistory] = useState<{ rating: ReviewRating; reviewed_at: string; next_review_at: string }[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  useEffect(() => {
    let active = true;
    getDueReviews(token).then((result) => { if (active) { setQueue(result); setError(""); } })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Unable to load review cards."); });
    return () => { active = false; };
  }, [token, refreshKey]);

  const card = queue?.cards[0];
  async function rate(rating: ReviewRating) {
    if (!card || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await rateReview(token, card.id, rating);
      setQueue(await getDueReviews(token)); setRevealed(false); setHistory(null);
      setNotice(`Saved. Next review ${new Date(result.next_review_at).toLocaleString()}.`);
      onReviewed();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to save review."); }
    finally { setBusy(false); }
  }
  async function showHistory() {
    if (!card) return;
    try { setHistory((await getReviewHistory(token, card.id)).events); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load history."); }
  }
  return <section className="student-panel due-review-panel" id="student-review" aria-label="Scheduled flashcard reviews">
    <div className="knowledge-heading"><div><span className="learning-eyebrow">Spaced repetition</span><h3>Review flashcards</h3></div><span>{queue?.summary.due_count ?? 0} due</span></div>
    {card ? <><p><strong>{card.topic}</strong> · {card.repetitions} successful review(s). Reveal the answer before rating your recall.</p>
      <button type="button" className="flashcard" onClick={() => setRevealed((value) => !value)} aria-label={revealed ? "Show question" : "Reveal answer"}>
        <span>{revealed ? "Answer" : "Question"}</span><strong>{revealed ? card.back : card.front}</strong>
      </button>
      {revealed && <div className="review-ratings">{RATINGS.map((item) => <button key={item.id} type="button" className="secondary-button" disabled={busy} onClick={() => void rate(item.id)}>{item.label}</button>)}</div>}
      <button type="button" className="review-history-toggle" onClick={() => void showHistory()}>View review history</button>
      {history && (history.length ? <ul className="review-history">{history.map((event, index) => <li key={`${event.reviewed_at}-${index}`}>{event.rating} on {new Date(event.reviewed_at).toLocaleString()} · next {new Date(event.next_review_at).toLocaleString()}</li>)}</ul> : <p>No previous reviews.</p>)}
    </> : <p>{queue ? "No cards are due now. Generate flashcards in Learning tools to start a review schedule." : "Loading review cards..."}</p>}
    {notice && <p role="status">{notice}</p>}{error && <p className="panel-error" role="alert">{error}</p>}
  </section>;
}
