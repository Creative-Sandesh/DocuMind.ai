
import asyncio
from uuid import UUID

import httpx

from fastapi import APIRouter, HTTPException

from app.schemas.rag_memory import (
    ConversationCreate,
    ConversationDetail,
    ConversationList,
    ConversationSummary,
    MemoryChatRequest,
    MemoryChatResponse,
)

from app.services.memory_service import (
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)

from app.services.rag_memory_service import (
    chat_with_memory,
)
from app.services.ollama_service import OllamaResponseError
from app.services.rag_service import DocumentNotFoundError
from app.services.vector_store_service import document_exists
from app.services.teacher_service import is_managed_document


router = APIRouter(
    prefix="/rag",
    tags=["RAG Conversation Memory"],
)


@router.post("/conversations", response_model=ConversationDetail, status_code=201)
async def start_conversation(request: ConversationCreate):
    selected_ids = [str(value) for value in request.document_ids]
    for document_id in selected_ids:
        if await asyncio.to_thread(is_managed_document, document_id):
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        if not await asyncio.to_thread(document_exists, document_id):
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
    return await asyncio.to_thread(create_conversation, selected_ids[0], selected_ids)


@router.get("/conversations", response_model=ConversationList)
async def get_conversations(document_id: UUID | None = None):
    conversations = await asyncio.to_thread(
        list_conversations,
        str(document_id) if document_id is not None else None,
    )
    return ConversationList(conversations=[ConversationSummary(**item) for item in conversations])


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def read_conversation(conversation_id: UUID):
    conversation = await asyncio.to_thread(get_conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(**conversation)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def remove_conversation(conversation_id: UUID):
    deleted = await asyncio.to_thread(delete_conversation, conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post(
    "/chat-memory",
    response_model=MemoryChatResponse,
)
async def rag_chat_memory(
    request: MemoryChatRequest,
):
    for value in [request.document_id, *request.document_ids]:
        if await asyncio.to_thread(is_managed_document, str(value)):
            raise HTTPException(status_code=404, detail="Document not found")
    try:
        result = await chat_with_memory(
            document_id=str(request.document_id),
            document_ids=[str(value) for value in request.document_ids],
            question=request.question,
            conversation_id=request.conversation_id,
        )

        return MemoryChatResponse(**result)

    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except httpx.ConnectError as exc:
        raise HTTPException(
            status_code=503,
            detail="Ollama service is unavailable",
        ) from exc

    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Ollama request timed out") from exc

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned an error: {exc.response.status_code}",
        ) from exc

    except OllamaResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
