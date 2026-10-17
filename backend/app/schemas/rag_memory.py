
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.chat import ChatSource, DocumentSelection


class MemoryChatRequest(DocumentSelection):
    question: str = Field(
        min_length=1,
        max_length=5000
    )
    conversation_id: UUID | None = None


class MemoryChatResponse(BaseModel):
    answer: str
    document_id: UUID
    document_ids: list[UUID]
    conversation_id: UUID
    history_length: int
    sources: list[ChatSource] = Field(default_factory=list)


class ConversationCreate(DocumentSelection):
    pass


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    sources: list[ChatSource] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    conversation_id: UUID
    document_id: UUID
    document_ids: list[UUID]
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[ConversationMessage]


class ConversationList(BaseModel):
    conversations: list[ConversationSummary]
