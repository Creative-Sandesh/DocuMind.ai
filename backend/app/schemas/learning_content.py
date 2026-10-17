"""Typed learning catalog requests and responses for Version 2."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


Difficulty = Literal["beginner", "intermediate", "advanced"]


class _CatalogInput(BaseModel):
    @field_validator("title", check_fields=False, mode="before")
    @classmethod
    def clean_title(cls, value):
        return value.strip() if isinstance(value, str) else value


class SubjectCreate(_CatalogInput):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)


class Subject(SubjectCreate):
    id: UUID
    created_at: datetime


class SubjectList(BaseModel):
    subjects: list[Subject]


class TopicCreate(_CatalogInput):
    subject_id: UUID
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    position: int = Field(default=0, ge=0)


class Topic(TopicCreate):
    id: UUID
    created_at: datetime


class TopicList(BaseModel):
    topics: list[Topic]


class LessonCreate(_CatalogInput):
    topic_id: UUID
    title: str = Field(min_length=1, max_length=160)
    summary: str | None = Field(default=None, max_length=2000)
    body: str | None = Field(default=None, max_length=100000)
    difficulty: Difficulty = "beginner"
    position: int = Field(default=0, ge=0)
    objectives: list[str] = Field(default_factory=list, max_length=20)
    source_document_ids: list[UUID] = Field(default_factory=list, max_length=5)

    @field_validator("objectives")
    @classmethod
    def validate_objectives(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 500 for value in cleaned):
            raise ValueError("Each objective must contain 1 to 500 characters")
        if len({value.casefold() for value in cleaned}) != len(cleaned):
            raise ValueError("Objectives must be unique within a lesson")
        return cleaned

    @field_validator("source_document_ids")
    @classmethod
    def validate_documents(cls, values: list[UUID]) -> list[UUID]:
        if len(set(values)) != len(values):
            raise ValueError("Source documents must be unique within a lesson")
        return values


class Lesson(LessonCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime


class LessonList(BaseModel):
    lessons: list[Lesson]
