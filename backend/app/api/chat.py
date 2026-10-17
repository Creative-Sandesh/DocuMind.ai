from fastapi import APIRouter, HTTPException
import httpx

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)

from app.services.rag_service import (
    DocumentNotFoundError,
    build_chat_sources,
    generate_rag_response,
)
from app.services.ollama_service import OllamaResponseError


router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse
)
async def chat(
    request: ChatRequest
):
    try:
        messages = [
            message.model_dump()
            for message in request.messages
        ]

        document_id = str(
            request.document_id
        )
        
        answer, retrieved_chunks = (
            await generate_rag_response(
                messages=messages,
                document_id=document_id,
                document_ids=[str(value) for value in request.document_ids],
            )
        )
        return ChatResponse(
            answer=answer,
            sources=build_chat_sources(retrieved_chunks),
        )

    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to connect to Ollama. "
                "Make sure Ollama is running."
            )
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Ollama request timed out."
        )
        
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned an error: {error.response.status_code}",
        ) from error

    except OllamaResponseError as error:
        raise HTTPException(
            status_code=502,
            detail=str(error),
        ) from error
