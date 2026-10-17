from uuid import UUID

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class ChatMessage(BaseModel):

    role: Literal[
        "user",
        "assistant"
    ]

    content: str = Field(
        min_length=1,
        max_length=5000
    )


class DocumentSelection(BaseModel):
    document_id: UUID | None = None
    document_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=5)

    @model_validator(mode="after")
    def validate_selection(self):
        ids = self.document_ids or ([self.document_id] if self.document_id else [])
        if not ids:
            raise ValueError("Select at least one document")
        if len(set(ids)) != len(ids):
            raise ValueError("Document selection contains duplicates")
        if self.document_id is not None and self.document_ids is not None:
            if self.document_id != ids[0]:
                raise ValueError("document_id must match the first selected document")
        self.document_id = ids[0]
        self.document_ids = ids
        return self


class ChatRequest(DocumentSelection):

    messages: list[
        ChatMessage
    ] = Field(
        min_length=1,
        max_length=20
    )


class ChatSource(BaseModel):

    chunk_id: str
    document_id: str
    filename: str
    chunk_index: int
    page_number: int | None = None
    text: str | None = None
    similarity: float


class ChatResponse(BaseModel):

    answer: str

    sources: list[
        ChatSource
    ] = Field(
        default_factory=list
    )
