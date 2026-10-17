"""Validate, save, and index PDF and TXT uploads."""

import asyncio
from itertools import islice
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.services.chunking_service import iter_text_chunks
from app.services.embedding_service import generate_embeddings
from app.services.vector_store_service import (
    delete_document_chunks,
    get_vector_count,
    store_chunks,
)


DOCUMENT_DIR = Path(__file__).resolve().parents[1] / "data" / "documents"
DOCUMENT_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE = 100 * 1024 * 1024
UPLOAD_READ_SIZE = 1024 * 1024
INDEX_BATCH_SIZE = 128


async def process_document(file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")

    document_id = str(uuid4())
    file_path = DOCUMENT_DIR / f"file{document_id}{extension}"
    size = 0
    indexing_started = False
    try:
        with file_path.open("wb") as saved_file:
            while block := await file.read(UPLOAD_READ_SIZE):
                size += len(block)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File size must be 100 MB or less.",
                    )
                saved_file.write(block)

        if size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        try:
            if extension == ".pdf":
                pages = await asyncio.to_thread(extract_pdf_pages, file_path)
                characters = sum(len(page_text) for _, page_text in pages)
                characters += max(len(pages) - 1, 0) * 2
                texts = (
                    (page_number, page_text)
                    for page_number, page_text in pages
                )
            else:
                text = await asyncio.to_thread(extract_txt_text, file_path)
                characters = len(text)
                texts = ((None, text),)
        except Exception as error:
            raise HTTPException(
                status_code=422, detail="Unable to extract text from document."
            ) from error

        if characters == 0 or (extension == ".txt" and not text.strip()):
            raise HTTPException(
                status_code=422, detail="No readable text found in document."
            )

        def chunks():
            chunk_index = 0
            for page_number, page_text in texts:
                for chunk in iter_text_chunks(page_text, document_id):
                    chunk["chunk_index"] = chunk_index
                    if page_number is not None:
                        chunk["page_number"] = page_number
                    chunk_index += 1
                    yield chunk

        pending_chunks = iter(chunks())
        chunk_count = 0
        embedding_dimension = 0
        while batch := list(islice(pending_chunks, INDEX_BATCH_SIZE)):
            embedded = await asyncio.to_thread(generate_embeddings, batch)
            if embedded and embedding_dimension == 0:
                embedding_dimension = len(embedded[0]["embedding"])
            indexing_started = True
            chunk_count += await asyncio.to_thread(store_chunks, embedded, file.filename)

        vector_store_total = await asyncio.to_thread(get_vector_count)
        return {
            "document_id": document_id,
            "filename": file.filename,
            "content_type": file.content_type or "unknown",
            "characters": characters,
            "chunk_count": chunk_count,
            "embedding_dimension": embedding_dimension,
            "stored_chunks": chunk_count,
            "vector_store_total": vector_store_total,
            "status": "processed",
        }
    except Exception:
        file_path.unlink(missing_ok=True)
        if indexing_started:
            await asyncio.to_thread(delete_document_chunks, document_id)
        raise


def extract_pdf_pages(file_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(file_path)
    return [
        (page_number, page_text)
        for page_number, page in enumerate(reader.pages, start=1)
        if (page_text := page.extract_text()) and page_text.strip()
    ]


def extract_pdf_text(file_path: Path) -> str:
    return "\n\n".join(text for _, text in extract_pdf_pages(file_path))


def extract_txt_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")
