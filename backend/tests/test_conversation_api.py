import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rag_memory import router
from app.api.chat import router as chat_router
from app.services import memory_service
from app.services.rag_memory_service import build_followup_retrieval_query
from app.services.ollama_service import OllamaResponseError


class ConversationApiTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_patch = patch.object(
            memory_service,
            "DB_PATH",
            Path(self.directory.name) / "conversations.sqlite3",
        )
        self.database_patch.start()
        self.memory_document_patch = patch(
            "app.api.rag_memory.document_exists", return_value=True
        )
        self.rag_document_patch = patch(
            "app.services.rag_service.document_exists", return_value=True
        )
        self.memory_document_patch.start()
        self.rag_document_patch.start()
        app = FastAPI()
        app.include_router(router)
        app.include_router(chat_router, prefix="/api")
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.rag_document_patch.stop()
        self.memory_document_patch.stop()
        self.database_patch.stop()
        self.directory.cleanup()

    def test_retrieval_query_uses_history_only_for_a_followup(self):
        history = [
            {"role": "user", "content": "Summarize the key points"},
            {"role": "assistant", "content": "First: safety. Second: privacy."},
        ]
        followup = build_followup_retrieval_query(
            "Explain the second point", history
        )
        self.assertIn("Second: privacy", followup)
        self.assertIn("Summarize the key points", followup)
        self.assertEqual(
            build_followup_retrieval_query("What is the author name?", history),
            "What is the author name?",
        )

    def test_failed_first_answer_does_not_leave_an_empty_session(self):
        with patch(
            "app.services.rag_memory_service.generate_rag_response",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("offline"),
        ):
            response = self.client.post(
                "/rag/chat-memory",
                json={"document_id": str(uuid4()), "question": "What is this?"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(memory_service.list_conversations(), [])

    def test_missing_document_is_not_treated_as_missing_context(self):
        document_id = str(uuid4())
        with patch("app.api.rag_memory.document_exists", return_value=False), patch(
            "app.services.rag_service.document_exists", return_value=False
        ):
            self.assertEqual(
                self.client.post(
                    "/rag/conversations", json={"document_id": document_id}
                ).status_code,
                404,
            )
            self.assertEqual(
                self.client.post(
                    "/rag/chat-memory",
                    json={"document_id": document_id, "question": "What is this?"},
                ).status_code,
                404,
            )
            self.assertEqual(
                self.client.post(
                    "/api/chat",
                    json={
                        "document_id": document_id,
                        "messages": [{"role": "user", "content": "What is this?"}],
                    },
                ).status_code,
                404,
            )
        self.assertEqual(memory_service.list_conversations(), [])

    def test_no_relevant_evidence_returns_no_sources_without_calling_ollama(self):
        document_id = str(uuid4())
        with patch(
            "app.services.rag_service.retrieve_relevant_chunks", return_value=[]
        ), patch(
            "app.services.rag_service.generate_response", new_callable=AsyncMock
        ) as generate:
            response = self.client.post(
                "/rag/chat-memory",
                json={"document_id": document_id, "question": "Unknown topic?"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("don't have enough information", response.json()["answer"])
        self.assertEqual(response.json()["sources"], [])
        generate.assert_not_called()

    def test_stateless_chat_returns_the_same_retrieved_source_contract(self):
        document_id = str(uuid4())
        chunk = {
            "chunk_id": "pdf-1",
            "text": "Page two fact",
            "metadata": {
                "document_id": document_id,
                "filename": "guide.pdf",
                "chunk_index": 4,
                "page_number": 2,
            },
            "similarity": 0.75,
        }
        with patch(
            "app.services.rag_service.retrieve_relevant_chunks", return_value=[chunk]
        ), patch(
            "app.services.rag_service.generate_response",
            new_callable=AsyncMock,
            return_value="The fact is on page two [1].",
        ):
            response = self.client.post(
                "/api/chat",
                json={
                    "document_id": document_id,
                    "messages": [{"role": "user", "content": "What is the fact?"}],
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"][0]["page_number"], 2)
        self.assertEqual(response.json()["sources"][0]["text"], "Page two fact")

    def test_invalid_model_response_returns_502_without_saving_turn(self):
        document_id = str(uuid4())
        chunk = {
            "chunk_id": "chunk-1",
            "text": "Relevant evidence",
            "metadata": {
                "document_id": document_id,
                "filename": "notes.txt",
                "chunk_index": 0,
            },
            "similarity": 0.8,
        }
        with patch(
            "app.services.rag_service.retrieve_relevant_chunks", return_value=[chunk]
        ), patch(
            "app.services.rag_service.generate_response",
            new_callable=AsyncMock,
            side_effect=OllamaResponseError("Ollama returned no answer text"),
        ):
            response = self.client.post(
                "/rag/chat-memory",
                json={"document_id": document_id, "question": "What is this?"},
            )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(memory_service.list_conversations(), [])

    def test_create_list_read_and_delete_session(self):
        document_id = str(uuid4())
        created = self.client.post(
            "/rag/conversations", json={"document_id": document_id}
        )
        self.assertEqual(created.status_code, 201)
        conversation_id = created.json()["conversation_id"]
        self.assertEqual(created.json()["messages"], [])

        memory_service.save_conversation_turn(
            UUID(conversation_id),
            "Question",
            "Answer",
        )
        listed = self.client.get(
            "/rag/conversations", params={"document_id": document_id}
        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["conversations"]), 1)
        self.assertEqual(listed.json()["conversations"][0]["title"], "Question")
        detail = self.client.get(f"/rag/conversations/{conversation_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["title"], "Question")
        self.assertEqual(len(detail.json()["messages"]), 2)

        deleted = self.client.delete(f"/rag/conversations/{conversation_id}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            self.client.get(f"/rag/conversations/{conversation_id}").status_code,
            404,
        )

    def test_memory_chat_saves_turns_and_rejects_document_switch(self):
        document_id = str(uuid4())
        chunk = {
            "chunk_id": "chunk-1",
            "text": "A supporting fact",
            "metadata": {
                "document_id": document_id,
                "filename": "notes.txt",
                "chunk_index": 0,
                "page_number": 2,
            },
            "similarity": 0.82,
        }
        with patch(
            "app.services.rag_service.retrieve_relevant_chunks",
            return_value=[chunk],
        ) as retrieve, patch(
            "app.services.rag_service.generate_response",
            new_callable=AsyncMock,
            return_value="Grounded answer",
        ):
            first = self.client.post(
                "/rag/chat-memory",
                json={"document_id": document_id, "question": "What is the fact?"},
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json()["sources"][0]["chunk_id"], "chunk-1")
            self.assertEqual(first.json()["sources"][0]["page_number"], 2)
            self.assertEqual(first.json()["sources"][0]["text"], "A supporting fact")
            conversation_id = first.json()["conversation_id"]
            second = self.client.post(
                "/rag/chat-memory",
                json={
                    "document_id": document_id,
                    "question": "Can you explain it?",
                    "conversation_id": conversation_id,
                },
            )
            self.assertEqual(second.status_code, 200)
            self.assertEqual(second.json()["history_length"], 4)
            self.assertIn("Grounded answer", retrieve.call_args.kwargs["query"])
            self.assertIn("Can you explain it?", retrieve.call_args.kwargs["query"])
            self.assertEqual(retrieve.call_args.kwargs["document_id"], document_id)
            self.assertEqual(
                len(self.client.get(f"/rag/conversations/{conversation_id}").json()["messages"]),
                4,
            )
            stored = self.client.get(f"/rag/conversations/{conversation_id}").json()
            self.assertEqual(stored["messages"][1]["sources"][0]["chunk_id"], "chunk-1")
            wrong_document = self.client.post(
                "/rag/chat-memory",
                json={
                    "document_id": str(uuid4()),
                    "question": "Another document?",
                    "conversation_id": conversation_id,
                },
            )
            self.assertEqual(wrong_document.status_code, 400)

    def test_multi_document_session_rejects_changed_selection(self):
        first_id, second_id = str(uuid4()), str(uuid4())
        selected = [first_id, second_id]
        with patch(
            "app.services.rag_memory_service.generate_rag_response",
            new_callable=AsyncMock,
            return_value=("Answer from selected documents", []),
        ) as generate:
            first = self.client.post(
                "/rag/chat-memory",
                json={"document_ids": selected, "question": "What do they say?"},
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(first.json()["document_ids"], selected)
            self.assertEqual(generate.call_args.kwargs["document_ids"], selected)
            conversation_id = first.json()["conversation_id"]
            stored = self.client.get(f"/rag/conversations/{conversation_id}").json()
            self.assertEqual(stored["document_ids"], selected)

            changed = self.client.post(
                "/rag/chat-memory",
                json={
                    "document_ids": [first_id],
                    "question": "And this one?",
                    "conversation_id": conversation_id,
                },
            )
            self.assertEqual(changed.status_code, 400)
            self.assertEqual(generate.await_count, 1)

    def test_selection_validation_rejects_empty_duplicates_and_over_limit(self):
        document_id = str(uuid4())
        for selection in ([], [document_id, document_id],
                          [str(uuid4()) for _ in range(6)]):
            response = self.client.post(
                "/rag/chat-memory",
                json={"document_ids": selection, "question": "Question"},
            )
            self.assertEqual(response.status_code, 422)

    def test_stateless_chat_passes_selected_document_ids(self):
        selected = [str(uuid4()), str(uuid4())]
        with patch(
            "app.api.chat.generate_rag_response",
            new_callable=AsyncMock,
            return_value=("Combined answer", []),
        ) as generate:
            response = self.client.post(
                "/api/chat",
                json={
                    "document_ids": selected,
                    "messages": [{"role": "user", "content": "Compare them"}],
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_args.kwargs["document_ids"], selected)


if __name__ == "__main__":
    unittest.main()
