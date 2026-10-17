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
