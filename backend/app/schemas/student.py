"""Student account and progress contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.learning_tools import AnswerSubmission, FlashcardResponse, QuizGenerateRequest, QuizResponse
from app.schemas.learning_content import Difficulty


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        parts = value.split("@")
        if len(parts) != 2 or not parts[0] or "." not in parts[1] or any(char.isspace() for char in value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be blank")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class TeacherRegisterRequest(RegisterRequest):
    teacher_code: str = Field(min_length=1, max_length=256)


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    preferred_language: Literal["english", "nepali", "bilingual"] = "english"
    learning_goals: str = Field(default="", max_length=1000)

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Display name cannot be blank")
        return value


class AttemptRequest(BaseModel):
    answers: list[AnswerSubmission]


class AdaptiveDecision(BaseModel):
    topic_status: Literal["insufficient_evidence", "weak", "developing", "strong"]
    selected_difficulty: Difficulty
    effective_difficulty: Difficulty
    reason: str


class SavedQuiz(BaseModel):
    quiz_id: UUID
    response: QuizResponse
    adaptive_decision: AdaptiveDecision | None = None


class StudentQuizGenerateRequest(QuizGenerateRequest):
    adaptive: bool = False


class PersonalizedQuizRequest(BaseModel):
    topic_key: str | None = Field(default=None, max_length=200)
    question_count: int = Field(default=5, ge=1, le=10)
    language: Literal["english", "nepali", "bilingual"] = "english"


class PersonalizedQuizPlan(BaseModel):
    topic_key: str
    topic: str
    topic_id: UUID | None = None
    status: Literal["weak", "unpracticed", "strong", "developing", "insufficient_evidence"]
    mastery_percent: float | None = None
    difficulty: Difficulty
    reason: str
    prior_errors: list[str]
    lesson_objectives: list[str]


class PersonalizedSavedQuiz(SavedQuiz):
    plan: PersonalizedQuizPlan


class SavedFlashcardDeck(FlashcardResponse):
    deck_id: UUID
    card_ids: list[UUID]


class ReviewRating(BaseModel):
    rating: Literal["again", "hard", "good", "easy"]


class SpeechTextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Text cannot be blank")
        return value


class StartStudyRequest(BaseModel):
    course_id: UUID | None = None


class TopicKnowledgeProfile(BaseModel):
    topic_key: str
    topic_id: UUID | None = None
    topic: str
    attempts: int = Field(ge=0)
    correct_answers: int = Field(ge=0)
    incorrect_answers: int = Field(ge=0)
    provisional_answers: int = Field(ge=0)
    recent_accuracy_percent: float | None = Field(default=None, ge=0, le=100)
    mastery_percent: float | None = Field(default=None, ge=0, le=100)
    last_practiced_at: datetime
    evidence: Literal["early", "supported"]
    status: Literal["insufficient_evidence", "weak", "developing", "strong"]
    status_reason: str
    recommended_difficulty: Difficulty


class KnowledgeProfileResponse(BaseModel):
    topics: list[TopicKnowledgeProfile]
    recent_window: int = Field(ge=1)
    method: str
