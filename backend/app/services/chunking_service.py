from uuid import uuid4


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def chunk_text(
    text: str,
    document_id: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
):
    return list(iter_text_chunks(text, document_id, chunk_size, chunk_overlap))


def iter_text_chunks(
    text: str,
    document_id: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
):
    if not text.strip():
        return

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be smaller than chunk size."
        )

    start = 0
    chunk_index = 0

    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        chunk_text_content = text[start:end].strip()

        if chunk_text_content:
            chunk = {
                "chunk_id": str(uuid4()),
                "document_id": document_id,
                "chunk_index": chunk_index,
                "text": chunk_text_content,
                "character_count": len(chunk_text_content)
            }

            yield chunk

            chunk_index += 1

        start += chunk_size - chunk_overlap


def _split_block(text: str, limit: int, overlap: int):
    """Split a long block near a line or word boundary."""
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + limit // 2, end)
            if boundary < 0:
                boundary = text.rfind(" ", start + limit // 2, end)
            if boundary > start:
                end = boundary
        part = text[start:end].strip()
        if part:
            yield part
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def iter_structured_chunks(
    pages,
    document_id: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
):
    """Keep page citations, sections, tables and equations intact where possible."""
    if chunk_size < 1 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Invalid structured chunk size or overlap")

    index = 0
    for page in pages:
        pending: list[str] = []
        pending_section = None

        def emit(text: str, section: str | None, kind: str):
            nonlocal index
            label = section[: min(160, max(0, chunk_size // 4))] if section else ""
            prefix = f"Section: {label}\n" if label and chunk_size > 20 else ""
            body_limit = max(1, chunk_size - len(prefix))
            for part in _split_block(text, body_limit, min(chunk_overlap, body_limit - 1)):
                content = prefix + part
                yield {
                    "chunk_id": str(uuid4()),
                    "document_id": document_id,
                    "chunk_index": index,
                    "page_number": page.page_number,
                    "extraction_method": page.extraction_method,
                    "section_title": section,
                    "block_type": kind,
                    "text": content,
                    "character_count": len(content),
                }
                index += 1

        for block in page.blocks:
            text = block.text.strip()
            if not text:
                continue
            section = block.section_title
            special = block.block_type in {"Table", "TableOfContents", "Equation", "EquationBlock", "Math", "Figure", "Picture"}
            pending_length = sum(len(item) + 2 for item in pending)
            if pending and (section != pending_section or special or pending_length + len(text) > chunk_size):
                yield from emit("\n\n".join(pending), pending_section, "Text")
                pending = []
            if special or len(text) > chunk_size:
                yield from emit(text, section, block.block_type)
            else:
                pending.append(text)
                pending_section = section
        if pending:
            yield from emit("\n\n".join(pending), pending_section, "Text")
