"""Local AI learning tools and practice evaluation endpoints."""

import asyncio

import httpx
from fastapi import APIRouter, HTTPException
from app.services.teacher_service import is_managed_document

from app.schemas.learning_tools import (
    FlashcardGenerateRequest, FlashcardResponse, LearningRequest, LessonResponse,
    QuizEvaluationRequest, QuizEvaluationResponse, QuizGenerateRequest,
    QuizResponse, VocabularyGenerateRequest, VocabularyResponse,
)
from app.services.learning_tools_service import (
    InvalidGeneratedContentError, LearningSourceError, evaluate_quiz,
    generate_flashcards, generate_lesson, generate_quiz, generate_vocabulary,
)
from app.services.ollama_service import OllamaResponseError


router = APIRouter(prefix="/api/learning", tags=["AI learning tools"])


async def _check_public_documents(request):
    for document_id in request.document_ids:
        if await asyncio.to_thread(is_managed_document, str(document_id)):
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")


async def _generate(operation, request):
    try:
        return await operation(request)
    except LearningSourceError as error:
        status = 404 if str(error).startswith("Document not found") else 422
        raise HTTPException(status_code=status, detail=str(error)) from error
    except InvalidGeneratedContentError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except httpx.ConnectError as error:
        raise HTTPException(status_code=503, detail="Ollama service is unavailable") from error
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="Ollama request timed out") from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=502, detail=f"Ollama returned HTTP {error.response.status_code}") from error
    except OllamaResponseError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post("/generate-lesson", response_model=LessonResponse)
async def lesson(request: LearningRequest):
    await _check_public_documents(request)
    return await _generate(generate_lesson, request)


@router.post("/generate-quiz", response_model=QuizResponse)
async def quiz(request: QuizGenerateRequest):
    await _check_public_documents(request)
    return await _generate(generate_quiz, request)


@router.post("/evaluate-quiz", response_model=QuizEvaluationResponse)
async def evaluate(request: QuizEvaluationRequest):
    try:
        return await asyncio.to_thread(evaluate_quiz, request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/generate-flashcards", response_model=FlashcardResponse)
async def flashcards(request: FlashcardGenerateRequest):
    await _check_public_documents(request)
    return await _generate(generate_flashcards, request)


@router.post("/generate-vocabulary", response_model=VocabularyResponse)
async def vocabulary(request: VocabularyGenerateRequest):
    await _check_public_documents(request)
    return await _generate(generate_vocabulary, request)
