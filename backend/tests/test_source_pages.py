import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import UploadFile

from app.services import document_service, vector_store_service


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


class SourcePageTests(unittest.IsolatedAsyncioTestCase):
    async def test_pdf_chunks_keep_original_page_numbers(self):
        stored = []
        with tempfile.TemporaryDirectory() as temporary_directory, patch.object(
            document_service, "DOCUMENT_DIR", Path(temporary_directory)
        ), patch.object(
            document_service, "PdfReader"
        ) as reader, patch.object(
            document_service, "generate_embeddings",
            side_effect=lambda chunks: [
                {**chunk, "embedding": [0.1, 0.2]} for chunk in chunks
            ],
        ), patch.object(
            document_service, "store_chunks", side_effect=lambda chunks, _: (stored.extend(chunks), len(chunks))[1]
        ), patch.object(document_service, "get_vector_count", return_value=2):
            reader.return_value.pages = [
                FakePage("First page evidence"),
                FakePage(None),
                FakePage("Third page evidence"),
            ]
            upload = UploadFile(filename="guide.pdf", file=io.BytesIO(b"%PDF"))
            result = await document_service.process_document(upload)

        self.assertEqual(result["stored_chunks"], 2)
        self.assertEqual(
            [chunk["page_number"] for chunk in stored], [1, 3]
        )
        self.assertEqual(
            [chunk["chunk_index"] for chunk in stored], [0, 1]
        )

    def test_vector_metadata_includes_page_only_when_available(self):
        chunks = [
            {
                "chunk_id": "pdf-chunk",
                "document_id": "document-id",
                "chunk_index": 0,
                "character_count": 5,
                "text": "alpha",
                "embedding": [0.1],
                "page_number": 3,
            },
            {
                "chunk_id": "txt-chunk",
                "document_id": "document-id",
                "chunk_index": 1,
                "character_count": 4,
                "text": "beta",
                "embedding": [0.2],
            },
        ]
        with patch.object(vector_store_service, "collection") as collection:
            vector_store_service.store_chunks(chunks, "guide.pdf")
        metadata = collection.upsert.call_args.kwargs["metadatas"]
        self.assertEqual(metadata[0]["page_number"], 3)
        self.assertNotIn("page_number", metadata[1])

    def test_deleting_document_removes_saved_upload(self):
        document_id = "12345678-1234-1234-1234-123456789abc"
        with tempfile.TemporaryDirectory() as temporary_directory, patch.object(
            vector_store_service, "DOCUMENT_DIR", Path(temporary_directory)
        ):
            saved_file = Path(temporary_directory) / f"file{document_id}.txt"
            saved_file.write_text("example", encoding="utf-8")
            vector_store_service.delete_document_file(document_id)
            self.assertFalse(saved_file.exists())


if __name__ == "__main__":
    unittest.main()
