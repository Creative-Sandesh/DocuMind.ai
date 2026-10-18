"""Contracts for local learning generation and practice evaluation."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.chat import ChatSource
from app.schemas.learning_content import Difficulty


Language = Literal["english", "nepali", "bilingual"]
QuestionType = Literal["multiple_choice", "true_false", "short_answer"]


class LearningRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=160)
    difficulty: Difficulty = "beginner"
    language: Language = "english"
    document_ids: list[UUID] = Field(default_factory=list, max_length=5)
    lesson_text: str | None = Field(default=None, max_length=12000)

    @model_validator(mode="after")
    def validate_input(self):
        self.topic = self.topic.strip()
        if not self.topic:
            raise ValueError("Topic cannot be blank")
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("Document IDs must be unique")
        return self


class LessonSection(BaseModel):
    heading: str = Field(min_length=1, max_length=160)
    explanation: str = Field(min_length=1, max_length=5000)
    examples: list[str] = Field(min_length=1, max_length=5)


class GeneratedLesson(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    introduction: str = Field(min_length=1, max_length=3000)
    sections: list[LessonSection] = Field(min_length=2, max_length=8)
    key_takeaways: list[str] = Field(min_length=2, max_length=8)
    practice_questions: list[str] = Field(min_length=1, max_length=5)
    summary: str = Field(min_length=1, max_length=3000)


class LessonResponse(BaseModel):
    lesson: GeneratedLesson
    difficulty: Difficulty
    language: Language
    sources: list[ChatSource] = Field(default_factory=list)


class QuizGenerateRequest(LearningRequest):
    question_count: int = Field(default=5, ge=1, le=10)
    question_types: list[QuestionType] = Field(default_factory=lambda: ["multiple_choice"])

    @model_validator(mode="after")
    def validate_types(self):
        if not self.question_types or len(set(self.question_types)) != len(self.question_types):
            raise ValueError("Select distinct question types")
        return self


class QuizQuestion(BaseModel):
    type: QuestionType
    question: str = Field(min_length=1, max_length=1000)
    options: list[str] = Field(default_factory=list, max_length=6)
    correct_answer: str = Field(min_length=1, max_length=1000)
    explanation: str = Field(min_length=1, max_length=2000)
    difficulty: Difficulty
    source_numbers: list[int] = Field(default_factory=list, max_length=5)
    rubric_keywords: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_question(self):
        self.question = self.question.strip()
        self.correct_answer = self.correct_answer.strip()
        self.options = [option.strip() for option in self.options]
        if self.type == "multiple_choice":
            if len(self.options) != 4 or len({option.casefold() for option in self.options}) != 4:
                raise ValueError("Multiple-choice questions need four distinct options")
            if self.correct_answer not in self.options:
                raise ValueError("The correct answer must match one option")
        elif self.type == "true_false":
            if self.correct_answer not in ("True", "False"):
                raise ValueError("True/false answers must be True or False")
            if self.options and self.options != ["True", "False"]:
                raise ValueError("True/false options must be True and False")
            self.options = ["True", "False"]
        elif self.options:
            raise ValueError("Short-answer questions cannot have choices")
        if self.type == "short_answer":
            self.rubric_keywords = [keyword.strip() for keyword in self.rubric_keywords]
            if not 2 <= len(self.rubric_keywords) <= 5 or any(not keyword for keyword in self.rubric_keywords):
                raise ValueError("Short answers need 2 to 5 rubric keywords")
            if len({keyword.casefold() for keyword in self.rubric_keywords}) != len(self.rubric_keywords):
                raise ValueError("Rubric keywords must be distinct")
        elif self.rubric_keywords:
            raise ValueError("Only short answers use rubric keywords")
        if any(number < 1 for number in self.source_numbers) or len(set(self.source_numbers)) != len(self.source_numbers):
            raise ValueError("Source numbers must be distinct positive integers")
        return self


class GeneratedQuiz(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    questions: list[QuizQuestion] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def no_duplicate_questions(self):
        normalized = {" ".join(question.question.casefold().split()) for question in self.questions}
        if len(normalized) != len(self.questions):
            raise ValueError("Quiz contains duplicate questions")
        return self


class QuizResponse(BaseModel):
    quiz: GeneratedQuiz
    sources: list[ChatSource] = Field(default_factory=list)
    practice_only: bool = True


class AnswerSubmission(BaseModel):
    question_index: int = Field(ge=0)
    answer: str = Field(max_length=2000)


class QuizEvaluationRequest(BaseModel):
    quiz: GeneratedQuiz
    answers: list[AnswerSubmission]


class AnswerFeedback(BaseModel):
    question_index: int
    question_type: QuestionType
    submitted_answer: str
    correct_answer: str
    correct: bool
    points: int
    explanation: str
    feedback: str
    provisional: bool = False


class QuizEvaluationResponse(BaseModel):
    score: int
    max_score: int
    results: list[AnswerFeedback]
    practice_only: bool = True


class FlashcardGenerateRequest(LearningRequest):
    count: int = Field(default=5, ge=1, le=12)
    mistakes: list[Annotated[str, Field(min_length=1, max_length=500)]] = Field(default_factory=list, max_length=10)


class Flashcard(BaseModel):
    front: str = Field(min_length=1, max_length=500)
    back: str = Field(min_length=1, max_length=2000)
    topic: str = Field(min_length=1, max_length=160)
    difficulty: Difficulty
    source_numbers: list[int] = Field(default_factory=list, max_length=5)


class FlashcardSet(BaseModel):
    flashcards: list[Flashcard] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def no_duplicates(self):
        if len({card.front.casefold().strip() for card in self.flashcards}) != len(self.flashcards):
            raise ValueError("Flashcards contain duplicate fronts")
        return self


class FlashcardResponse(BaseModel):
    flashcards: list[Flashcard]
    sources: list[ChatSource] = Field(default_factory=list)


class VocabularyGenerateRequest(LearningRequest):
    count: int = Field(default=5, ge=1, le=12)


class VocabularyItem(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    definition: str = Field(min_length=1, max_length=1000)
    example: str = Field(min_length=1, max_length=1000)
    nepali_meaning: str = Field(min_length=1, max_length=500)
    practice_question: str = Field(min_length=1, max_length=500)
    source_numbers: list[int] = Field(default_factory=list, max_length=5)


class VocabularySet(BaseModel):
    words: list[VocabularyItem] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def no_duplicates(self):
        if len({item.word.casefold() for item in self.words}) != len(self.words):
            raise ValueError("Vocabulary list contains duplicate words")
        return self


class VocabularyResponse(BaseModel):
    words: list[VocabularyItem]
    sources: list[ChatSource] = Field(default_factory=list)
