import unittest
from unittest.mock import patch
from uuid import uuid4

import chromadb
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.documents import router as document_router
from app.services import retrieval_service, vector_store_service
from app.services.retrieval_ranking_service import rank_chunks


def chunk(document_id: str, chunk_id: str, text: str, similarity: float,
          filename: str = "notes.txt") -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": {
            "document_id": document_id,
            "filename": filename,
            "chunk_index": 0,
        },
        "distance": 1 - similarity,
        "similarity": similarity,
    }


class MultiRetrievalTests(unittest.TestCase):
    def test_chroma_query_filters_by_document_and_filename(self):
        client = chromadb.EphemeralClient()
        collection = client.create_collection(
            name=f"phase4_{uuid4().hex}",
            embedding_function=None,
            configuration={"hnsw": {"space": "cosine"}},
        )
        first_id, second_id = str(uuid4()), str(uuid4())
        collection.upsert(
            ids=["one", "two", "three"],
            embeddings=[[1.0, 0.0], [0.9, 0.1], [0.8, 0.2]],
            documents=["first", "second", "third"],
            metadatas=[
                {"document_id": first_id, "filename": "a.txt", "chunk_index": 0},
                {"document_id": second_id, "filename": "b.txt", "chunk_index": 0},
                {"document_id": first_id, "filename": "other.txt", "chunk_index": 1},
            ],
        )
        with patch.object(vector_store_service, "collection", collection):
            filtered = vector_store_service.search_chunks(
                [1.0, 0.0], first_id, n_results=10, filename="a.txt"
            )
            all_first = vector_store_service.search_chunks(
                [1.0, 0.0], first_id, n_results=10
            )
        self.assertEqual([item["chunk_id"] for item in filtered], ["one"])
        self.assertEqual({item["chunk_id"] for item in all_first}, {"one", "three"})

    def test_cross_document_query_embeds_once(self):
        selected = [str(uuid4()), str(uuid4()), str(uuid4())]
        with patch.object(
            retrieval_service, "generate_query_embedding", return_value=[0.1, 0.2]
        ) as embed, patch.object(
            retrieval_service, "search_chunks", return_value=[]
        ) as search:
            retrieval_service.retrieve_across_documents("comparison", selected)
        embed.assert_called_once_with("comparison")
        self.assertEqual(
            [call.kwargs["document_id"] for call in search.call_args_list], selected
        )
        self.assertTrue(all(call.kwargs["query_embedding"] == [0.1, 0.2]
                            for call in search.call_args_list))

    def test_ranking_keeps_document_coverage_without_duplicate_text(self):
        first_id, second_id, foreign_id = (str(uuid4()) for _ in range(3))
        candidates = [
            chunk(first_id, "a1", "Encrypted backups are daily.", 0.94),
            chunk(first_id, "a2", " encrypted   backups are daily. ", 0.92),
            chunk(first_id, "a3", "Retention is 30 days.", 0.89),
            chunk(second_id, "b1", "Encrypted backups are weekly.", 0.51),
            chunk(foreign_id, "x", "Private fact.", 0.99),
            chunk(second_id, "b2", "Unrelated.", 0.1),
        ]
        ranked = rank_chunks(
            candidates, [first_id, second_id], limit=3,
            min_similarity=0.35, balanced=True,
        )
        self.assertEqual([item["chunk_id"] for item in ranked], ["a1", "b1", "a3"])


class SearchApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(document_router, prefix="/api/documents")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_search_filters_selected_ids_and_filename(self):
        first_id, second_id, foreign_id = (str(uuid4()) for _ in range(3))
        candidates = [
            chunk(first_id, "a", "Selected evidence", 0.8, "a.txt"),
            chunk(second_id, "b", "Wrong filename", 0.9, "b.txt"),
            chunk(foreign_id, "x", "Unselected evidence", 0.99, "a.txt"),
        ]
        with patch("app.api.documents.document_exists", return_value=True), patch(
            "app.api.documents.retrieve_across_documents", return_value=candidates
        ) as retrieve:
            response = self.client.post(
                "/api/documents/search",
                json={
                    "document_ids": [first_id, second_id],
                    "query": "evidence",
                    "filename": "a.txt",
                    "min_similarity": 0.35,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["chunk_id"] for item in response.json()["results"]], ["a"])
        self.assertEqual(retrieve.call_args.kwargs["document_ids"], [first_id, second_id])
        self.assertEqual(retrieve.call_args.kwargs["filename"], "a.txt")

    def test_missing_document_is_rejected_before_search(self):
        document_id = str(uuid4())
        with patch("app.api.documents.document_exists", return_value=False), patch(
            "app.api.documents.retrieve_across_documents"
        ) as retrieve:
            response = self.client.post(
                "/api/documents/search",
                json={"document_ids": [document_id], "query": "question"},
            )
        self.assertEqual(response.status_code, 404)
        retrieve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
