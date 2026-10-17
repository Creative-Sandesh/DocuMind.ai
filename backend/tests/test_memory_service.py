import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from app.services import memory_service


class ConversationStorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_patch = patch.object(
            memory_service,
            "DB_PATH",
            Path(self.directory.name) / "conversations.sqlite3",
        )
        self.database_patch.start()

    def tearDown(self):
        self.database_patch.stop()
        self.directory.cleanup()

    def test_turns_survive_new_database_connections_and_are_document_bound(self):
        document_id = str(uuid4())
        other_document_id = str(uuid4())
        conversation = memory_service.create_conversation(document_id)
        conversation_id = conversation["conversation_id"]

        memory_service.save_conversation_turn(
            conversation_id, "First question", "First answer"
        )
        memory_service.save_conversation_turn(
            conversation_id, "Follow-up", "Second answer"
        )

        reloaded = memory_service.get_conversation(conversation_id)
        self.assertEqual(reloaded["document_id"], document_id)
        self.assertEqual(
            [(message["role"], message["content"]) for message in reloaded["messages"]],
            [
                ("user", "First question"),
                ("assistant", "First answer"),
                ("user", "Follow-up"),
                ("assistant", "Second answer"),
            ],
        )
        self.assertEqual(len(memory_service.list_conversations(document_id)), 1)
        self.assertEqual(memory_service.list_conversations(other_document_id), [])
        with self.assertRaisesRegex(ValueError, "another document"):
            memory_service.get_or_create_conversation(other_document_id, conversation_id)

    def test_prompt_history_is_bounded_but_saved_messages_are_complete(self):
        document_id = str(uuid4())
        conversation_id = memory_service.create_conversation(document_id)["conversation_id"]
        for index in range(8):
            memory_service.save_conversation_turn(
                conversation_id, f"Question {index}", f"Answer {index}"
            )

        _, history = memory_service.get_or_create_conversation(
            document_id, conversation_id
        )
        self.assertEqual(len(history), memory_service.MAX_HISTORY_MESSAGES)
        self.assertEqual(history[0]["content"], "Question 2")
        self.assertEqual(history[-1]["content"], "Answer 7")
        self.assertEqual(len(memory_service.get_conversation(conversation_id)["messages"]), 16)

    def test_deleting_session_removes_its_messages(self):
        document_id = str(uuid4())
        conversation_id = memory_service.create_conversation(document_id)["conversation_id"]
        memory_service.save_conversation_turn(conversation_id, "Q", "A")

        self.assertTrue(memory_service.delete_conversation(conversation_id))
        self.assertIsNone(memory_service.get_conversation(conversation_id))
        self.assertFalse(memory_service.delete_conversation(conversation_id))
        with self.assertRaisesRegex(ValueError, "not found"):
            memory_service.save_conversation_turn(conversation_id, "Q2", "A2")

    def test_existing_database_is_migrated_to_save_sources(self):
        with closing(sqlite3.connect(memory_service.DB_PATH)) as database:
            database.execute(
                "CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "conversation_id TEXT NOT NULL, role TEXT NOT NULL, "
                "content TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
        document_id = str(uuid4())
        conversation_id = memory_service.create_conversation(document_id)[
            "conversation_id"
        ]
        source = {"chunk_id": "chunk-1", "page_number": 2}
        memory_service.save_conversation_turn(
            conversation_id, "Question", "Answer", [source]
        )
        messages = memory_service.get_conversation(conversation_id)["messages"]
        self.assertEqual(messages[0]["sources"], [])
        self.assertEqual(messages[1]["sources"], [source])

    def test_legacy_conversation_migrates_and_new_selection_is_bound(self):
        old_document_id, second_document_id = str(uuid4()), str(uuid4())
        old_conversation_id = str(uuid4())
        with closing(sqlite3.connect(memory_service.DB_PATH)) as database:
            database.execute(
                "CREATE TABLE conversations (id TEXT PRIMARY KEY, "
                "document_id TEXT NOT NULL, created_at TEXT NOT NULL, "
                "updated_at TEXT NOT NULL)"
            )
            database.execute(
                "INSERT INTO conversations VALUES (?, ?, ?, ?)",
                (old_conversation_id, old_document_id, "2026-01-01", "2026-01-01"),
            )
            database.commit()

        self.assertEqual(
            memory_service.get_conversation(UUID(old_conversation_id))["document_ids"],
            [old_document_id],
        )
        selected = [old_document_id, second_document_id]
        created = memory_service.create_conversation(old_document_id, selected)
        conversation_id = created["conversation_id"]
        self.assertEqual(
            memory_service.get_conversation(conversation_id)["document_ids"], selected
        )
        self.assertEqual(len(memory_service.list_conversations(second_document_id)), 1)
        with self.assertRaisesRegex(ValueError, "selection"):
            memory_service.get_or_create_conversation(
                old_document_id, conversation_id, [old_document_id]
            )


if __name__ == "__main__":
    unittest.main()
