"""Teacher-owned course, content and quiz input contracts."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.learning_content import Difficulty
from app.schemas.learning_tools import GeneratedQuiz, QuizGenerateRequest


class NamedInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value


class CourseInput(NamedInput):
    pass


class CourseTopicInput(NamedInput):
    position: int = Field(default=0, ge=0)


class CourseLessonInput(BaseModel):
    topic_id: UUID
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=2000)
    body: str = Field(default="", max_length=100000)
    difficulty: Difficulty = "beginner"
    position: int = Field(default=0, ge=0)
    objectives: list[str] = Field(default_factory=list, max_length=20)
    source_document_ids: list[UUID] = Field(default_factory=list, max_length=5)

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Title cannot be blank")
        return value

    @field_validator("objectives")
    @classmethod
    def clean_objectives(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item or len(item) > 500 for item in cleaned) or len(set(cleaned)) != len(cleaned):
            raise ValueError("Objectives must be distinct and 1 to 500 characters")
        return cleaned


class MaterialInput(NamedInput):
    pass


class EnrollmentInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class TeacherQuizInput(BaseModel):
    topic_id: UUID | None = None
    quiz: GeneratedQuiz


class TeacherQuizGenerateInput(QuizGenerateRequest):
    topic_id: UUID | None = None


class QuizAssignInput(BaseModel):
    student_ids: list[UUID] = Field(default_factory=list, max_length=200)

    @field_validator("student_ids")
    @classmethod
    def distinct_students(cls, value: list[UUID]) -> list[UUID]:
        if len(set(value)) != len(value):
            raise ValueError("Student IDs must be unique")
        return value
