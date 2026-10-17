"""Multi-turn chat using the same document RAG pipeline as the regular chat API."""

import asyncio
import re
from uuid import UUID

from app.services.memory_service import (
    MAX_HISTORY_MESSAGES,
    create_conversation,
    get_or_create_conversation,
    save_conversation_turn,
)
from app.services.rag_service import build_chat_sources, generate_rag_response


FOLLOWUP_REFERENCE = re.compile(
    r"\b(it|its|this|that|these|those|they|them|their|first|second|"
    r"third|former|latter|previous|earlier|above|more)\b",
    re.IGNORECASE,
)


def build_followup_retrieval_query(
    question: str, history: list[dict[str, str]]
) -> str:
    """Add the last turn to retrieval only when the question refers back to it."""
    if not history or not FOLLOWUP_REFERENCE.search(question):
        return question

    previous_question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"),
        "",
    )
    previous_answer = next(
        (item["content"] for item in reversed(history) if item["role"] == "assistant"),
        "",
    )
    return "\n".join(
        part
        for part in (previous_question[:400], previous_answer[:600], question)
        if part
    )


async def chat_with_memory(
    document_id: str,
    question: str,
    conversation_id: UUID | None = None,
    document_ids: list[str] | None = None,
) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")
    selected_ids = document_ids or [document_id]

    history: list[dict[str, str]] = []
    if conversation_id is not None:
        _, history = await asyncio.to_thread(
            get_or_create_conversation, document_id, conversation_id, selected_ids
        )

    messages = [*history, {"role": "user", "content": question}]
    retrieval_query = build_followup_retrieval_query(question, history)
    answer, chunks = await generate_rag_response(
        messages=messages,
        document_id=document_id,
        document_ids=selected_ids,
        retrieval_query=retrieval_query,
    )

    if conversation_id is None:
        conversation = await asyncio.to_thread(
            create_conversation, document_id, selected_ids
        )
        conversation_id = conversation["conversation_id"]

    sources = build_chat_sources(chunks)
    await asyncio.to_thread(
        save_conversation_turn, conversation_id, question, answer, sources
    )

    return {
        "answer": answer,
        "document_id": document_id,
        "document_ids": selected_ids,
        "conversation_id": conversation_id,
        "history_length": min(len(history) + 2, MAX_HISTORY_MESSAGES),
        "sources": sources,
    }
