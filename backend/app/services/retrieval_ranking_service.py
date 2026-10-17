"""Select useful, nonredundant evidence while preserving document attribution."""

import re


def _normalized_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def rank_chunks(
    chunks: list[dict],
    document_ids: list[str],
    limit: int,
    min_similarity: float = 0.0,
    balanced: bool = False,
    filename: str | None = None,
) -> list[dict]:
    """Filter by selection, remove repeated text within a document, and rank."""
    if limit < 1:
        return []

    selected = set(document_ids)
    candidates = [
        chunk for chunk in chunks
        if isinstance(chunk.get("metadata"), dict)
        and chunk["metadata"].get("document_id") in selected
        and (filename is None or chunk["metadata"].get("filename") == filename)
        and chunk.get("similarity", -1) >= min_similarity
        and isinstance(chunk.get("text"), str)
        and chunk["text"].strip()
    ]
    candidates.sort(key=lambda chunk: chunk["similarity"], reverse=True)

    unique = []
    seen: set[tuple[str, str]] = set()
    for chunk in candidates:
        key = (chunk["metadata"]["document_id"], _normalized_text(chunk["text"]))
        if key not in seen:
            seen.add(key)
            unique.append(chunk)

    if not balanced:
        return unique[:limit]

    chosen = []
    chosen_ids = set()
    for document_id in document_ids:
        best = next(
            (chunk for chunk in unique if chunk["metadata"]["document_id"] == document_id),
            None,
        )
        if best is not None:
            chosen.append(best)
            chosen_ids.add(best["chunk_id"])
        if len(chosen) == limit:
            return chosen

    for chunk in unique:
        if chunk["chunk_id"] not in chosen_ids:
            chosen.append(chunk)
            if len(chosen) == limit:
                break
    return chosen
