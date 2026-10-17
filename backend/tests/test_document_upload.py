import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, UploadFile

from app.services import document_service


class DocumentUploadTests(unittest.IsolatedAsyncioTestCase):
    async def test_limit_accepts_exact_size_and_rejects_larger_file(self):
        self.assertEqual(document_service.MAX_FILE_SIZE, 100 * 1024 * 1024)
        with tempfile.TemporaryDirectory() as temporary_directory, patch.object(
            document_service, "DOCUMENT_DIR", Path(temporary_directory)
        ), patch.object(document_service, "MAX_FILE_SIZE", 7), patch.object(
            document_service, "UPLOAD_READ_SIZE", 3
        ), patch.object(
            document_service,
            "generate_embeddings",
            side_effect=lambda chunks: [
                {**chunk, "embedding": [0.1, 0.2]} for chunk in chunks
            ],
        ), patch.object(
            document_service, "store_chunks", side_effect=lambda chunks, _: len(chunks)
        ), patch.object(document_service, "get_vector_count", return_value=1):
            accepted = await document_service.process_document(
                UploadFile(filename="notes.txt", file=io.BytesIO(b"1234567"))
            )
            self.assertEqual(accepted["characters"], 7)
            self.assertEqual(accepted["chunk_count"], 1)
            self.assertEqual(accepted["embedding_dimension"], 2)

            with self.assertRaises(HTTPException) as rejection:
                await document_service.process_document(
                    UploadFile(filename="large.txt", file=io.BytesIO(b"12345678"))
                )
            self.assertEqual(rejection.exception.status_code, 413)
            self.assertEqual(len(list(Path(temporary_directory).glob("*.txt"))), 1)

    async def test_indexing_uses_bounded_batches(self):
        batch_sizes = []

        def embed(chunks):
            batch_sizes.append(len(chunks))
            return [{**chunk, "embedding": [0.1]} for chunk in chunks]

        with tempfile.TemporaryDirectory() as temporary_directory, patch.object(
            document_service, "DOCUMENT_DIR", Path(temporary_directory)
        ), patch.object(document_service, "INDEX_BATCH_SIZE", 2), patch.object(
            document_service, "generate_embeddings", side_effect=embed
        ), patch.object(
            document_service, "store_chunks", side_effect=lambda chunks, _: len(chunks)
        ), patch.object(document_service, "get_vector_count", return_value=3):
            result = await document_service.process_document(
                UploadFile(filename="notes.txt", file=io.BytesIO(b"a" * 2200))
            )

        self.assertEqual(batch_sizes, [2, 1])
        self.assertEqual(result["chunk_count"], 3)


if __name__ == "__main__":
    unittest.main()
