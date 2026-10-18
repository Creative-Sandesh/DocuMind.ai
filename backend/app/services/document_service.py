"""Validate, save, and index PDF and TXT uploads."""

import asyncio
import json
import logging
from itertools import islice
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from app.services.chunking_service import iter_structured_chunks, iter_text_chunks
from app.services.embedding_service import generate_embeddings
from app.services.marker_service import MarkerUnavailableError, ParsedPdf, convert_pdf
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
logger = logging.getLogger(__name__)


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
                parsed = await asyncio.to_thread(convert_pdf, file_path)
                characters = sum(len(block.text) for page in parsed.pages for block in page.blocks)
            else:
                text = await asyncio.to_thread(extract_txt_text, file_path)
                characters = len(text)
        except MarkerUnavailableError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except Exception as error:
            raise HTTPException(
                status_code=422,
                detail=("Unable to read TXT as UTF-8." if extension == ".txt" else
                        "Unable to parse document locally. Check that the PDF is valid and not encrypted."),
            ) from error

        if characters == 0 or (extension == ".txt" and not text.strip()):
            raise HTTPException(
                status_code=422, detail="No readable text found in document."
            )

        def chunks():
            if extension == ".pdf":
                yield from iter_structured_chunks(parsed.pages, document_id)
            else:
                yield from iter_text_chunks(text, document_id)

        pending_chunks = iter(chunks())
        chunk_count = 0
        embedding_dimension = 0
        while batch := list(islice(pending_chunks, INDEX_BATCH_SIZE)):
            embedded = await asyncio.to_thread(generate_embeddings, batch)
            if embedded and embedding_dimension == 0:
                embedding_dimension = len(embedded[0]["embedding"])
            indexing_started = True
            chunk_count += await asyncio.to_thread(store_chunks, embedded, file.filename)

        if extension == ".pdf":
            await asyncio.to_thread(save_marker_artifacts, document_id, parsed)
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
        if indexing_started:
            try:
                await asyncio.to_thread(delete_document_chunks, document_id)
            except Exception:
                logger.exception("Could not roll back vectors for document %s", document_id)
        try:
            await asyncio.to_thread(remove_document_artifacts, document_id)
        except Exception:
            logger.exception("Could not remove files for document %s", document_id)
        raise


def remove_document_artifacts(document_id: str) -> None:
    for path in DOCUMENT_DIR.glob(f"file{document_id}.*"):
        if path.is_file():
            path.unlink(missing_ok=True)


def save_marker_artifacts(document_id: str, parsed: ParsedPdf) -> None:
    """Retain structured pages and extracted images beside the original PDF."""
    image_files = {}
    markdown = parsed.markdown
    for index, (original_name, content) in enumerate(sorted(parsed.images.items())):
        suffix = Path(original_name).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
            suffix = ".png"
        stored_name = f"file{document_id}.image-{index}{suffix}"
        (DOCUMENT_DIR / stored_name).write_bytes(content)
        image_files[original_name] = stored_name
        markdown = markdown.replace(f"({original_name})", f"({stored_name})")

    (DOCUMENT_DIR / f"file{document_id}.marker.md").write_text(markdown, encoding="utf-8")
    structure = {
        "parser": "marker",
        "pages": [
            {
                "page_number": page.page_number,
                "extraction_method": page.extraction_method,
                "blocks": [
                    {"block_type": block.block_type, "text": block.text,
                     "section_title": block.section_title,
                     "marker_id": block.marker_id, "bbox": block.bbox}
                    for block in page.blocks
                ],
            }
            for page in parsed.pages
        ],
        "images": image_files,
    }
    (DOCUMENT_DIR / f"file{document_id}.marker.json").write_text(
        json.dumps(structure, ensure_ascii=False), encoding="utf-8"
    )


def extract_pdf_pages(file_path: Path) -> list[tuple[int, str]]:
    parsed = convert_pdf(file_path)
    return [
        (page.page_number, "\n\n".join(block.text for block in page.blocks))
        for page in parsed.pages if page.blocks
    ]


def extract_pdf_text(file_path: Path) -> str:
    return "\n\n".join(text for _, text in extract_pdf_pages(file_path))


def extract_txt_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")
