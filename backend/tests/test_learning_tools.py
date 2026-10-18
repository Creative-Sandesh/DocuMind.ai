"""Structured local generation and deterministic quiz scoring checks."""

import json
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.learning_tools import router


LESSON = {
    "title": "Python loops", "introduction": "Loops repeat code.",
    "sections": [
        {"heading": "For", "explanation": "A for loop iterates [1].", "examples": ["for x in xs: print(x)"]},
        {"heading": "While", "explanation": "A while loop checks a condition [1].", "examples": ["while ready: run()"]},
    ],
    "key_takeaways": ["For iterates", "While checks conditions"],
    "practice_questions": ["When would you use while?"],
    "summary": "Choose the loop for the task.",
}
QUIZ = {
    "title": "Loops quiz",
    "questions": [
        {"type": "multiple_choice", "question": "Which loop iterates?", "options": ["for", "while", "if", "def"],
         "correct_answer": "for", "explanation": "For iterates.", "difficulty": "beginner",
         "source_numbers": [], "rubric_keywords": []},
        {"type": "true_false", "question": "A loop can repeat code.", "options": ["True", "False"],
         "correct_answer": "True", "explanation": "Loops repeat.", "difficulty": "beginner",
         "source_numbers": [], "rubric_keywords": []},
        {"type": "short_answer", "question": "Explain a for loop.", "options": [],
         "correct_answer": "It iterates over items.", "explanation": "Iteration visits each item.",
         "difficulty": "beginner", "source_numbers": [], "rubric_keywords": ["iterates", "items"]},
    ],
}


class LearningToolsTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_lesson_levels_and_bilingual_prompt(self):
        bilingual = json.loads(json.dumps(LESSON))
        bilingual["introduction"] += " नेपाली: लुपले कोड दोहोर्याउँछ।"
        bilingual["summary"] += " नेपाली: सही लुप छान्नुहोस्।"
        for section in bilingual["sections"]:
            section["explanation"] += " नेपाली: उदाहरण हेर्नुहोस्।"
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(bilingual)) as generate:
            response = self.client.post("/api/learning/generate-lesson", json={
                "topic": "Python loops", "difficulty": "advanced", "language": "bilingual",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lesson"]["sections"][0]["heading"], "For")
        self.assertEqual(response.json()["language"], "bilingual")
        system = generate.call_args.args[0][0]["content"]
        self.assertIn("English sentence and a Nepali", system)
        self.assertIn("deeper concepts", system)

    def test_nepali_request_rejects_english_only_output(self):
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(LESSON)):
            response = self.client.post("/api/learning/generate-lesson", json={
                "topic": "loops", "language": "nepali",
            })
        self.assertEqual(response.status_code, 502)

    def test_document_grounding_and_bad_citations(self):
        document_id = str(uuid4())
        chunk = {"chunk_id": "chunk-1", "text": "Loops repeat code", "similarity": 0.9,
                 "metadata": {"document_id": document_id, "filename": "loops.pdf", "chunk_index": 0}}
        grounded_quiz = json.loads(json.dumps(QUIZ))
        grounded_quiz["questions"] = grounded_quiz["questions"][:1]
        grounded_quiz["questions"][0]["source_numbers"] = [1]
        with patch("app.services.learning_tools_service.document_exists", return_value=True), patch(
            "app.services.learning_tools_service.retrieve_across_documents", return_value=[chunk]
        ), patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                 return_value=json.dumps(grounded_quiz)) as generate:
            response = self.client.post("/api/learning/generate-quiz", json={
                "topic": "loops", "document_ids": [document_id], "question_count": 1,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"][0]["chunk_id"], "chunk-1")
        self.assertIn("Loops repeat code", generate.call_args.args[0][1]["content"])
        grounded_quiz["questions"][0]["source_numbers"] = [2]
        with patch("app.services.learning_tools_service.document_exists", return_value=True), patch(
            "app.services.learning_tools_service.retrieve_across_documents", return_value=[chunk]
        ), patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                 return_value=json.dumps(grounded_quiz)):
            invalid = self.client.post("/api/learning/generate-quiz", json={
                "topic": "loops", "document_ids": [document_id], "question_count": 1,
            })
        self.assertEqual(invalid.status_code, 502)

    def test_missing_or_irrelevant_document_does_not_call_model(self):
        document_id = str(uuid4())
        with patch("app.services.learning_tools_service.document_exists", return_value=False), patch(
            "app.services.learning_tools_service.generate_response", new_callable=AsyncMock
        ) as generate:
            missing = self.client.post("/api/learning/generate-lesson", json={
                "topic": "loops", "document_ids": [document_id],
            })
        self.assertEqual(missing.status_code, 404)
        generate.assert_not_called()
        with patch("app.services.learning_tools_service.document_exists", return_value=True), patch(
            "app.services.learning_tools_service.retrieve_across_documents", return_value=[]
        ), patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock) as generate:
            irrelevant = self.client.post("/api/learning/generate-lesson", json={
                "topic": "loops", "document_ids": [document_id],
            })
        self.assertEqual(irrelevant.status_code, 422)
        generate.assert_not_called()

    def test_quiz_validation_and_practice_scoring(self):
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(QUIZ)):
            generated = self.client.post("/api/learning/generate-quiz", json={
                "topic": "loops", "question_count": 3,
                "question_types": ["multiple_choice", "true_false", "short_answer"],
            })
        self.assertEqual(generated.status_code, 200)
        evaluated = self.client.post("/api/learning/evaluate-quiz", json={
            "quiz": generated.json()["quiz"], "answers": [
                {"question_index": 0, "answer": "for"},
                {"question_index": 1, "answer": "false"},
                {"question_index": 2, "answer": "It iterates over items"},
            ],
        })
        self.assertEqual(evaluated.status_code, 200)
        self.assertEqual(evaluated.json()["score"], 2)
        self.assertTrue(evaluated.json()["results"][2]["provisional"])
        self.assertIn("not a definitive grade", evaluated.json()["results"][2]["feedback"])
        missing = self.client.post("/api/learning/evaluate-quiz", json={
            "quiz": QUIZ, "answers": [{"question_index": 0, "answer": "for"}],
        })
        self.assertEqual(missing.status_code, 422)

    def test_quiz_recovers_from_invalid_options_and_constrains_count(self):
        invalid = json.loads(json.dumps(QUIZ))
        invalid["questions"] = invalid["questions"][:1]
        invalid["questions"][0]["options"] = ["for", "while", "while", "if"]
        valid = json.loads(json.dumps(QUIZ))
        valid["questions"] = valid["questions"][:1]
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   side_effect=[json.dumps(invalid), json.dumps(valid)]) as generate:
            response = self.client.post("/api/learning/generate-quiz", json={
                "topic": "loops", "question_count": 1,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.await_count, 2)
        schema = generate.call_args.kwargs["response_format"]
        self.assertEqual(schema["properties"]["questions"]["minItems"], 1)
        self.assertEqual(schema["properties"]["questions"]["maxItems"], 1)
        question_schema = schema["$defs"]["QuizQuestion"]
        self.assertIn("options", question_schema["required"])
        self.assertEqual(question_schema["properties"]["type"]["enum"], ["multiple_choice"])
        self.assertEqual(question_schema["properties"]["options"]["minItems"], 4)
        self.assertEqual(question_schema["properties"]["options"]["maxItems"], 4)
        self.assertIn("four distinct options", generate.call_args.args[0][1]["content"])

    def test_rejects_duplicate_questions_and_invalid_model_json(self):
        duplicate = json.loads(json.dumps(QUIZ))
        duplicate["questions"][1]["question"] = duplicate["questions"][0]["question"]
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(duplicate)):
            response = self.client.post("/api/learning/generate-quiz", json={
                "topic": "loops", "question_count": 3,
                "question_types": ["multiple_choice", "true_false", "short_answer"],
            })
        self.assertEqual(response.status_code, 502)
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value="not JSON"):
            invalid = self.client.post("/api/learning/generate-lesson", json={"topic": "loops"})
        self.assertEqual(invalid.status_code, 502)

    def test_flashcards_vocabulary_and_ollama_failure(self):
        cards = {"flashcards": [{"front": "What is a loop?", "back": "Repetition", "topic": "loops",
                                "difficulty": "beginner", "source_numbers": []}]}
        words = {"words": [{"word": "iterate", "definition": "Repeat steps", "example": "We iterate over items.",
                            "nepali_meaning": "दोहोर्‍याउनु", "practice_question": "What does iterate mean?",
                            "source_numbers": []}]}
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(cards)):
            response = self.client.post("/api/learning/generate-flashcards", json={
                "topic": "loops", "count": 1, "mistakes": ["Confused loop types"],
            })
        self.assertEqual(response.status_code, 200)
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(words)):
            response = self.client.post("/api/learning/generate-vocabulary", json={"topic": "loops", "count": 1})
        self.assertEqual(response.status_code, 200)
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   side_effect=httpx.ConnectError("offline")):
            offline = self.client.post("/api/learning/generate-lesson", json={"topic": "loops"})
        self.assertEqual(offline.status_code, 503)

    def test_vocabulary_recovers_from_wrong_count(self):
        word = {"word": "iterate", "definition": "Repeat steps", "example": "We iterate over items.",
                "nepali_meaning": "दोहोर्याउनु", "practice_question": "What does iterate mean?",
                "source_numbers": []}
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   side_effect=[json.dumps({"words": []}), json.dumps({"words": [word]})]) as generate:
            response = self.client.post("/api/learning/generate-vocabulary", json={
                "topic": "loops", "count": 1,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.await_count, 2)
        schema = generate.call_args.kwargs["response_format"]
        self.assertEqual(schema["properties"]["words"]["minItems"], 1)
        self.assertEqual(schema["properties"]["words"]["maxItems"], 1)
        self.assertIn("previous JSON failed validation", generate.call_args.args[0][1]["content"])

    def test_strips_unreferenced_labels_without_documents(self):
        cards = {"flashcards": [{"front": "Loop?", "back": "Repeat", "topic": "loops",
                                "difficulty": "beginner", "source_numbers": [1]}]}
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(cards)):
            response = self.client.post("/api/learning/generate-flashcards", json={
                "topic": "loops", "count": 1,
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["flashcards"][0]["source_numbers"], [])

    def test_rejects_hindi_mislabeled_as_nepali_meaning(self):
        words = {"words": [{"word": "loop", "definition": "Repetition", "example": "The loop repeats.",
                            "nepali_meaning": "यह दोहराने के लिए होता है", "practice_question": "Meaning?",
                            "source_numbers": []}]}
        with patch("app.services.learning_tools_service.generate_response", new_callable=AsyncMock,
                   return_value=json.dumps(words)):
            response = self.client.post("/api/learning/generate-vocabulary", json={
                "topic": "loops", "count": 1, "language": "bilingual",
            })
        self.assertEqual(response.status_code, 502)


if __name__ == "__main__":
    unittest.main()
