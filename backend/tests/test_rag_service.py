import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.ollama_service import (
    OllamaResponseError,
    generate_response,
    prepare_ollama_messages,
)
from app.services.rag_service import (
    DocumentNotFoundError,
    build_chat_sources,
    generate_rag_response,
)
from app.services.vector_store_service import get_document_overview_chunks


class GroundedRagTests(unittest.IsolatedAsyncioTestCase):
    def test_overview_selection_prefers_contents_to_preface(self):
        document_id = str(uuid4())
        stored = {
            "ids": ["preface", "contents", "title"],
            "documents": [
                "Preface: curricular contents are useful.",
                "Section: Contents\nChapter 1: Motion\nChapter 2: Waves",
                "PHYSICS Grade 12",
            ],
            "metadatas": [
                {"document_id": document_id, "filename": "physics.pdf", "chunk_index": 2},
                {"document_id": document_id, "filename": "physics.pdf", "chunk_index": 5},
                {"document_id": document_id, "filename": "physics.pdf", "chunk_index": 0},
            ],
        }
        with patch("app.services.vector_store_service.collection.get", return_value=stored):
            selected = get_document_overview_chunks(document_id, 2)
        self.assertEqual([item["chunk_id"] for item in selected], ["title", "contents"])

    async def test_comparison_prompt_uses_both_documents_and_labels(self):
        first_id, second_id = str(uuid4()), str(uuid4())

        def evidence(document_id, text, similarity):
            return {
                "chunk_id": document_id,
                "text": text,
                "metadata": {
                    "document_id": document_id,
                    "filename": "policy.txt",
                    "chunk_index": 0,
                },
                "similarity": similarity,
            }

        candidates = [
            evidence(first_id, "Both policies encrypt backups. Daily retention is 30 days.", 0.9),
            evidence(second_id, "Both policies encrypt backups. Weekly retention is 90 days.", 0.6),
        ]
        with patch(
            "app.services.rag_service.document_exists", return_value=True
        ), patch(
            "app.services.rag_service.retrieve_across_documents",
            return_value=candidates,
        ), patch(
            "app.services.rag_service.generate_response",
            new_callable=AsyncMock,
            return_value="They agree on encryption [1] [2] but differ on retention [1] [2].",
        ) as generate:
            answer, sources = await generate_rag_response(
                [{"role": "user", "content": "Compare agreements and differences"}],
                document_ids=[first_id, second_id],
            )

        self.assertIn("agree on encryption", answer)
        self.assertEqual({source["metadata"]["document_id"] for source in sources},
                         {first_id, second_id})
        prompt = generate.await_args.args[0]
        self.assertIn("Agreements and Differences", prompt[0]["content"])
        self.assertIn(f"document {first_id}", prompt[-1]["content"])
        self.assertIn(f"document {second_id}", prompt[-1]["content"])

    async def test_comparison_without_evidence_from_every_document_skips_model(self):
        first_id, second_id = str(uuid4()), str(uuid4())
        candidate = {
            "chunk_id": "one",
            "text": "Only the first document discusses backups.",
            "metadata": {
                "document_id": first_id,
                "filename": "first.txt",
                "chunk_index": 0,
            },
            "similarity": 0.8,
        }
        with patch(
            "app.services.rag_service.document_exists", return_value=True
        ), patch(
            "app.services.rag_service.retrieve_across_documents",
            return_value=[candidate],
        ), patch(
            "app.services.rag_service.generate_response", new_callable=AsyncMock
        ) as generate:
            answer, sources = await generate_rag_response(
                [{"role": "user", "content": "Compare these documents"}],
                document_ids=[first_id, second_id],
            )
        self.assertIn("can't make a supported comparison", answer)
        self.assertEqual(len(sources), 1)
        generate.assert_not_called()

    async def test_multi_document_prompt_uses_only_selected_evidence(self):
        first_id, second_id, foreign_id = (str(uuid4()) for _ in range(3))

        def chunk(document_id, text):
            return {
                "chunk_id": document_id,
                "text": text,
                "metadata": {
                    "document_id": document_id,
                    "filename": f"{document_id}.txt",
                    "chunk_index": 0,
                },
                "similarity": 0.8,
            }

        def retrieve(*, document_ids, **_):
            return [
                *(chunk(document_id, f"Fact from {document_id}")
                  for document_id in document_ids),
                chunk(foreign_id, "Private unselected fact"),
            ]

        with patch(
            "app.services.rag_service.document_exists", return_value=True
        ), patch(
            "app.services.rag_service.retrieve_across_documents",
            side_effect=retrieve,
        ) as search, patch(
            "app.services.rag_service.generate_response",
            new_callable=AsyncMock,
            return_value="Both documents provide facts [1] [2].",
        ) as generate:
            _, evidence = await generate_rag_response(
                [{"role": "user", "content": "What do they say?"}],
                document_ids=[first_id, second_id],
            )

        self.assertEqual({item["metadata"]["document_id"] for item in evidence},
                         {first_id, second_id})
        self.assertEqual(search.call_count, 1)
        self.assertNotIn("Private unselected fact", generate.await_args.args[0][-1]["content"])

    async def test_multi_document_request_rejects_missing_selection(self):
        first_id, missing_id = str(uuid4()), str(uuid4())
        with patch(
            "app.services.rag_service.document_exists",
            side_effect=lambda document_id: document_id == first_id,
        ), patch(
            "app.services.rag_service.retrieve_across_documents"
        ) as search:
            with self.assertRaises(DocumentNotFoundError):
                await generate_rag_response(
                    [{"role": "user", "content": "Question"}],
                    document_ids=[first_id, missing_id],
                )
        search.assert_not_called()

    async def test_broad_overview_can_use_evidence_below_normal_cutoff(self):
        document_id = str(uuid4())
        chunk = {
            "chunk_id": "overview",
            "text": "The book explains statistical learning methods.",
            "metadata": {
                "document_id": document_id,
                "filename": "book.pdf",
                "chunk_index": 0,
            },
            "similarity": 0.28,
        }
        with patch(
            "app.services.rag_service.document_exists", return_value=True
        ), patch(
            "app.services.rag_service.retrieve_relevant_chunks", return_value=[chunk]
        ), patch(
            "app.services.rag_service.generate_response",
            new_callable=AsyncMock,
            return_value="It explains statistical learning [1].",
        ) as generate:
            _, overview_sources = await generate_rag_response(
                [{"role": "user", "content": "Summarize the main topic"}],
                document_id,
            )
            _, unrelated_sources = await generate_rag_response(
                [{"role": "user", "content": "What are tomorrow's lottery numbers?"}],
                document_id,
            )
        self.assertEqual(len(overview_sources), 1)
        self.assertEqual(unrelated_sources, [])
        self.assertEqual(generate.await_count, 1)

    async def test_broad_document_question_uses_contents_when_vector_search_is_weak(self):
        document_id = str(uuid4())
        outline = [
            {
                "chunk_id": "title", "text": "PHYSICS Grade 12",
                "metadata": {"document_id": document_id, "filename": "physics.pdf", "chunk_index": 0},
                "similarity": 0.0, "selection_method": "outline",
            },
            {
                "chunk_id": "contents", "text": "Contents: Rotational Dynamics; Wave Motion; Electrical Circuits",
                "metadata": {"document_id": document_id, "filename": "physics.pdf", "chunk_index": 5},
                "similarity": 0.0, "selection_method": "outline",
            },
        ]
        with patch("app.services.rag_service.document_exists", return_value=True), patch(
            "app.services.rag_service.retrieve_relevant_chunks", return_value=[]
        ), patch("app.services.rag_service.get_document_overview_chunks", return_value=outline), patch(
            "app.services.rag_service.generate_response", new_callable=AsyncMock,
            return_value="The book covers rotational dynamics, waves, and circuits [2].",
        ) as generate:
            answer, evidence = await generate_rag_response(
                [{"role": "user", "content": "Summarize the main points"}], document_id,
            )
        self.assertIn("rotational dynamics", answer)
        self.assertEqual([item["chunk_id"] for item in evidence], ["title", "contents"])
        self.assertEqual(build_chat_sources(evidence)[1]["selection_method"], "outline")
        self.assertIn("Contents: Rotational Dynamics", generate.await_args.args[0][-1]["content"])

    async def test_broad_overview_covers_all_five_selected_documents(self):
        document_ids = [str(uuid4()) for _ in range(5)]

        def outline(document_id, _limit):
            return [
                {"chunk_id": f"{document_id}-{index}", "text": f"Document {document_id} part {index}",
                 "metadata": {"document_id": document_id, "filename": "notes.txt", "chunk_index": index},
                 "similarity": 0.0, "selection_method": "outline"}
                for index in range(2)
            ]

        with patch("app.services.rag_service.document_exists", return_value=True), patch(
            "app.services.rag_service.retrieve_across_documents", return_value=[]
        ), patch("app.services.rag_service.get_document_overview_chunks", side_effect=outline), patch(
            "app.services.rag_service.generate_response", new_callable=AsyncMock,
            return_value="Overview from the selected documents.",
        ):
            _, evidence = await generate_rag_response(
                [{"role": "user", "content": "Summarize the main points"}],
                document_ids=document_ids,
            )
        self.assertEqual({item["metadata"]["document_id"] for item in evidence}, set(document_ids))

    async def test_ollama_rejects_success_response_without_answer(self):
        response = MagicMock()
        response.json.return_value = {"message": {"content": "  "}}
        with patch("app.services.ollama_service.httpx.AsyncClient") as client_type:
            client_type.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=response
            )
            with self.assertRaises(OllamaResponseError):
                await generate_response([{"role": "user", "content": "Question"}])

    async def test_prompt_uses_only_selected_document_evidence(self):
        document_id = str(uuid4())
        other_document_id = str(uuid4())

        def chunk(chunk_id, text, source_document, similarity):
            return {
                "chunk_id": chunk_id,
                "text": text,
                "metadata": {
                    "document_id": source_document,
                    "filename": "guide.pdf",
                    "chunk_index": 2,
                    "page_number": 3,
                },
                "similarity": similarity,
            }

        selected = chunk("selected", "The policy allows review.", document_id, 0.8)
        foreign = chunk("foreign", "Private document fact.", other_document_id, 0.9)
        weak = chunk("weak", "Unrelated topic.", document_id, 0.1)
        messages = [
            {"role": "user", "content": "Summarize the policy"},
            {"role": "assistant", "content": "An earlier answer"},
            {"role": "user", "content": "What does it allow?"},
        ]

        with patch(
            "app.services.rag_service.document_exists", return_value=True
        ), patch(
            "app.services.rag_service.retrieve_relevant_chunks",
            return_value=[foreign, selected, weak],
        ), patch(
            "app.services.rag_service.generate_response",
            new_callable=AsyncMock,
            return_value="Review is allowed [1].",
        ) as generate:
            answer, evidence = await generate_rag_response(messages, document_id)

        self.assertEqual(answer, "Review is allowed [1].")
        self.assertEqual([item["chunk_id"] for item in evidence], ["selected"])
        sent = generate.await_args.args[0]
        self.assertEqual(sent[0]["role"], "system")
        self.assertNotIn("The policy allows review", sent[0]["content"])
        self.assertIn("untrusted", sent[0]["content"])
        self.assertEqual(sent[2]["content"], "An earlier answer")
        self.assertIn("[1] guide.pdf, chunk 2, page 3", sent[-1]["content"])
        self.assertNotIn("Private document fact", sent[-1]["content"])
        self.assertNotIn("Unrelated topic", sent[-1]["content"])
        sources = build_chat_sources(evidence)
        self.assertEqual(sources[0]["page_number"], 3)
        self.assertEqual(sources[0]["text"], "The policy allows review.")

    async def test_last_message_must_be_a_nonempty_user_question(self):
        with self.assertRaisesRegex(ValueError, "last message"):
            await generate_rag_response(
                [{"role": "assistant", "content": "Previous answer"}], str(uuid4())
            )
        with self.assertRaisesRegex(ValueError, "empty"):
            await generate_rag_response(
                [{"role": "user", "content": "   "}], str(uuid4())
            )

    def test_ollama_keeps_rag_instructions_when_history_is_long(self):
        system = {"role": "system", "content": "Grounded instructions"}
        history = [
            {"role": "user", "content": f"Question {index}"}
            for index in range(25)
        ]
        prepared = prepare_ollama_messages([system, *history])
        self.assertEqual(prepared[0], system)
        self.assertEqual(len(prepared), 21)
        self.assertEqual(prepared[1]["content"], "Question 5")
        self.assertEqual(prepared[-1]["content"], "Question 24")


if __name__ == "__main__":
    unittest.main()
