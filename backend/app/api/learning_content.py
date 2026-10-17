"""Version 2 learning catalog endpoints."""

import asyncio
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.learning_content import (
    Lesson, LessonCreate, LessonList, Subject, SubjectCreate, SubjectList,
    Topic, TopicCreate, TopicList,
)
from app.services import learning_content_service as catalog
from app.services.vector_store_service import document_exists


router = APIRouter(prefix="/api/learning", tags=["Learning catalog"])
T = TypeVar("T")


async def _call(function: Callable[..., T], *args) -> T:
    try:
        return await asyncio.to_thread(function, *args)
    except catalog.CatalogNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except catalog.CatalogConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/subjects", response_model=Subject, status_code=201)
async def add_subject(request: SubjectCreate):
    return await _call(catalog.create_subject, request)


@router.get("/subjects", response_model=SubjectList)
async def get_subjects():
    return {"subjects": await _call(catalog.list_subjects)}


@router.post("/topics", response_model=Topic, status_code=201)
async def add_topic(request: TopicCreate):
    return await _call(catalog.create_topic, request)


@router.get("/topics", response_model=TopicList)
async def get_topics(subject_id: UUID | None = None):
    return {"topics": await _call(catalog.list_topics, subject_id)}


@router.post("/lessons", response_model=Lesson, status_code=201)
async def add_lesson(request: LessonCreate):
    for document_id in request.source_document_ids:
        if not await asyncio.to_thread(document_exists, str(document_id)):
            raise HTTPException(status_code=404, detail=f"Source document not found: {document_id}")
    return await _call(catalog.create_lesson, request)


@router.get("/lessons", response_model=LessonList)
async def get_lessons(topic_id: UUID | None = None):
    return {"lessons": await _call(catalog.list_lessons, topic_id)}


@router.get("/lessons/{lesson_id}", response_model=Lesson)
async def read_lesson(lesson_id: UUID):
    return await _call(catalog.get_lesson, lesson_id)
