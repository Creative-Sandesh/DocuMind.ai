"""Teacher-only course, material, quiz and analytics endpoints."""

import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.learning_tools import _generate
from app.api.student import current_user
from app.schemas.student import TeacherRegisterRequest
from app.schemas.teacher import (
    CourseInput, CourseLessonInput, CourseTopicInput, EnrollmentInput, MaterialInput,
    QuizAssignInput, TeacherQuizGenerateInput, TeacherQuizInput,
)
from app.services import auth_service, teacher_analytics_service, teacher_service
from app.services.document_service import DOCUMENT_DIR, process_document
from app.services.learning_tools_service import generate_quiz
from app.services.vector_store_service import delete_document_chunks, delete_document_file


router = APIRouter(prefix="/api/teacher", tags=["Teacher"])


async def current_teacher(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="Teacher account required")
    return user


async def _call(function, *args):
    try:
        return await asyncio.to_thread(function, *args)
    except teacher_service.NotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except teacher_service.Conflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/register", status_code=201)
async def register_teacher(request: TeacherRegisterRequest):
    try:
        return await asyncio.to_thread(auth_service.register_teacher, request)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/courses")
async def courses(user: dict = Depends(current_teacher)):
    return {"courses": await asyncio.to_thread(teacher_service.list_courses, user["id"])}


@router.post("/courses", status_code=201)
async def create_course(request: CourseInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.create_course, user["id"], request)


@router.put("/courses/{course_id}")
async def update_course(course_id: UUID, request: CourseInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.update_course, user["id"], str(course_id), request)


@router.get("/courses/{course_id}/topics")
async def topics(course_id: UUID, user: dict = Depends(current_teacher)):
    return {"topics": await _call(teacher_service.list_topics, user["id"], str(course_id))}


@router.post("/courses/{course_id}/topics", status_code=201)
async def add_topic(course_id: UUID, request: CourseTopicInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.create_topic, user["id"], str(course_id), request)


@router.get("/courses/{course_id}/lessons")
async def lessons(course_id: UUID, user: dict = Depends(current_teacher)):
    return {"lessons": await _call(teacher_service.list_lessons, user["id"], str(course_id))}


@router.post("/courses/{course_id}/lessons", status_code=201)
async def add_lesson(course_id: UUID, request: CourseLessonInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.create_lesson, user["id"], str(course_id), request)


@router.put("/courses/{course_id}/lessons/{lesson_id}")
async def edit_lesson(course_id: UUID, lesson_id: UUID, request: CourseLessonInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.update_lesson, user["id"], str(course_id), str(lesson_id), request)


@router.get("/courses/{course_id}/materials")
async def materials(course_id: UUID, user: dict = Depends(current_teacher)):
    return {"materials": await _call(teacher_service.list_materials, user["id"], str(course_id))}


@router.post("/courses/{course_id}/materials", status_code=201)
async def upload_material(course_id: UUID, file: UploadFile = File(...), user: dict = Depends(current_teacher)):
    await _call(teacher_service.owned_course, user["id"], str(course_id))
    document = await process_document(file)
    try:
        return await _call(teacher_service.add_material, user["id"], str(course_id), document)
    except Exception:
        await asyncio.to_thread(delete_document_chunks, document["document_id"])
        await asyncio.to_thread(delete_document_file, document["document_id"])
        raise


@router.put("/courses/{course_id}/materials/{material_id}")
async def edit_material(course_id: UUID, material_id: UUID, request: MaterialInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.update_material, user["id"], str(course_id), str(material_id), request.title, request.description)


@router.get("/courses/{course_id}/materials/{material_id}/download")
async def download_material(course_id: UUID, material_id: UUID, user: dict = Depends(current_teacher)):
    material = await _call(teacher_service.get_material, user["id"], str(course_id), str(material_id))
    original_file = DOCUMENT_DIR / f"file{material['document_id']}{Path(material['filename']).suffix.lower()}"
    if not original_file.is_file():
        raise HTTPException(status_code=404, detail="Material file not found")
    return FileResponse(original_file, filename=material["filename"])


@router.delete("/courses/{course_id}/materials/{material_id}", status_code=204)
async def remove_material(course_id: UUID, material_id: UUID, user: dict = Depends(current_teacher)):
    material = await _call(teacher_service.get_material, user["id"], str(course_id), str(material_id))
    await asyncio.to_thread(delete_document_chunks, material["document_id"])
    await asyncio.to_thread(delete_document_file, material["document_id"])
    await _call(teacher_service.remove_material, user["id"], str(course_id), str(material_id))


@router.get("/courses/{course_id}/students")
async def students(course_id: UUID, user: dict = Depends(current_teacher)):
    return {"students": await _call(teacher_service.list_students, user["id"], str(course_id))}


@router.post("/courses/{course_id}/students", status_code=201)
async def enroll(course_id: UUID, request: EnrollmentInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.enroll_student, user["id"], str(course_id), request.email)


@router.delete("/courses/{course_id}/students/{student_id}", status_code=204)
async def unenroll(course_id: UUID, student_id: UUID, user: dict = Depends(current_teacher)):
    await _call(teacher_service.remove_student, user["id"], str(course_id), str(student_id))


@router.get("/courses/{course_id}/quizzes")
async def quizzes(course_id: UUID, user: dict = Depends(current_teacher)):
    return {"quizzes": await _call(teacher_service.list_quizzes, user["id"], str(course_id))}


@router.post("/courses/{course_id}/quizzes", status_code=201)
async def create_quiz(course_id: UUID, request: TeacherQuizInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.save_quiz, user["id"], str(course_id), request)


@router.post("/courses/{course_id}/quizzes/generate", status_code=201)
async def generate_teacher_quiz(course_id: UUID, request: TeacherQuizGenerateInput, user: dict = Depends(current_teacher)):
    course = await _call(teacher_service.owned_course, user["id"], str(course_id))
    if request.topic_id:
        topics = await _call(teacher_service.list_topics, user["id"], str(course_id))
        if str(request.topic_id) not in {topic["id"] for topic in topics}:
            raise HTTPException(status_code=404, detail="Topic not found in this course")
    materials = await _call(teacher_service.list_materials, user["id"], str(course_id))
    material_ids = {item["document_id"] for item in materials}
    if any(str(document_id) not in material_ids for document_id in request.document_ids):
        raise HTTPException(status_code=404, detail="Course material not found")
    response = await _generate(generate_quiz, request)
    return await _call(teacher_service.save_quiz, user["id"], course["id"], TeacherQuizInput(topic_id=request.topic_id, quiz=response.quiz), response.sources)


@router.put("/quizzes/{quiz_id}")
async def edit_quiz(quiz_id: UUID, request: TeacherQuizInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.update_quiz, user["id"], str(quiz_id), request)


@router.post("/quizzes/{quiz_id}/publish")
async def publish(quiz_id: UUID, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.publish_quiz, user["id"], str(quiz_id))


@router.post("/quizzes/{quiz_id}/assign")
async def assign(quiz_id: UUID, request: QuizAssignInput, user: dict = Depends(current_teacher)):
    return await _call(teacher_service.assign_quiz, user["id"], str(quiz_id), [str(value) for value in request.student_ids])


@router.get("/quizzes/{quiz_id}/results")
async def results(quiz_id: UUID, user: dict = Depends(current_teacher)):
    return {"results": await _call(teacher_service.quiz_results, user["id"], str(quiz_id))}


@router.get("/courses/{course_id}/analytics")
async def analytics(course_id: UUID, user: dict = Depends(current_teacher)):
    return await _call(teacher_analytics_service.course_analytics, user["id"], str(course_id))
