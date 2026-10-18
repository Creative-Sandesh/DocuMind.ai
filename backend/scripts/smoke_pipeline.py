"""Exercise scanned PDF -> Marker -> embeddings -> ephemeral Chroma -> local Ollama."""

import argparse
import asyncio
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import UUID

import chromadb
from chromadb.config import Settings
from fastapi import UploadFile
from PIL import Image, ImageDraw, ImageFont

from app.services import document_service, vector_store_service
from app.schemas.learning_tools import QuizGenerateRequest
from app.services.learning_tools_service import generate_quiz
from app.services.rag_service import generate_rag_response


def synthetic_scan(font_path: Path) -> bytes:
    image = Image.new("RGB", (1200, 1600), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path), 60)
    draw.text((80, 120), "PHYSICS LESSON", font=font, fill="black")
    draw.text((80, 250), "Energy is conserved.", font=font, fill="black")
    draw.text((80, 380), "Force equals mass times acceleration.", font=font, fill="black")
    output = BytesIO()
    image.save(output, "PDF", resolution=150)
    return output.getvalue()


async def run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, help="Optional local PDF; otherwise use a generated scanned page")
    parser.add_argument("--question", default="What is conserved?")
    parser.add_argument("--quiz", action="store_true", help="Also generate a one-question grounded quiz")
    args = parser.parse_args()
    if args.pdf:
        if not args.pdf.is_file():
            parser.error("PDF does not exist")
        pdf_bytes = args.pdf.read_bytes()
    else:
        font_path = Path(__file__).resolve().parents[1] / ".models" / "marker" / "GoNotoCurrent-Regular.ttf"
        pdf_bytes = synthetic_scan(font_path)

    client = chromadb.EphemeralClient(settings=Settings(anonymized_telemetry=False))
    collection = client.get_or_create_collection(
        "marker_smoke", embedding_function=None, configuration={"hnsw": {"space": "cosine"}}
    )
    with TemporaryDirectory() as directory, patch.object(
        document_service, "DOCUMENT_DIR", Path(directory)
    ), patch.object(vector_store_service, "collection", collection):
        result = await document_service.process_document(
            UploadFile(filename="smoke.pdf", file=BytesIO(pdf_bytes))
        )
        answer, sources = await generate_rag_response(
            [{"role": "user", "content": args.question}], result["document_id"]
        )
        print(f"chunks={result['chunk_count']} sources={len(sources)}")
        print("pages=" + ",".join(str(source["metadata"].get("page_number")) for source in sources))
        print("answer=" + answer[:500])
        if args.quiz:
            quiz = await generate_quiz(QuizGenerateRequest(
                topic="Energy", difficulty="beginner", language="english",
                document_ids=[UUID(result["document_id"])], question_count=1,
                question_types=["true_false"],
            ))
            print(f"quiz_questions={len(quiz.quiz.questions)} quiz_sources={len(quiz.sources)}")


if __name__ == "__main__":
    asyncio.run(run())
