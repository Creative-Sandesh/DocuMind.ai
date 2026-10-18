"""Student authentication and owner-scoped learning records."""

import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.learning_tools import _generate
from app.schemas.learning_tools import FlashcardGenerateRequest, FlashcardResponse, LearningRequest, LessonResponse, VocabularyGenerateRequest, VocabularyResponse
from app.schemas.student import AttemptRequest, KnowledgeProfileResponse, LoginRequest, PersonalizedQuizRequest, PersonalizedSavedQuiz, ProfileUpdate, RegisterRequest, ReviewRating, SavedFlashcardDeck, SavedQuiz, SpeechTextRequest, StartStudyRequest, StudentQuizGenerateRequest
from app.schemas.learning_tools import QuizGenerateRequest
from app.services import adaptive_learning_service, auth_service, knowledge_profile_service, personalized_learning_service, recommendation_service, spaced_repetition_service, speech_service, student_service, teacher_service
from app.services.learning_tools_service import generate_flashcards, generate_lesson, generate_quiz, generate_vocabulary
from app.services.document_service import DOCUMENT_DIR


router = APIRouter(prefix="/api/student", tags=["Student"])
bearer = HTTPBearer(auto_error=False)


async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to continue")
    user = await asyncio.to_thread(auth_service.get_user, credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user


async def current_student(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Student account required")
    return user


async def _owned(function, *args):
    try:
        return await asyncio.to_thread(function, *args)
    except student_service.StudentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except student_service.StudentConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/register", status_code=201)
async def register(request: RegisterRequest):
    try:
        return await asyncio.to_thread(auth_service.register, request)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/login")
async def login(request: LoginRequest):
    result = await asyncio.to_thread(auth_service.login, request.email, request.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return result


@router.post("/logout", status_code=204)
async def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), user: dict = Depends(current_user)):
    await asyncio.to_thread(auth_service.logout, credentials.credentials)


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return user


@router.put("/profile")
async def update_profile(request: ProfileUpdate, user: dict = Depends(current_student)):
    return await asyncio.to_thread(auth_service.update_profile, user["id"], request)


@router.post("/quizzes/generate", response_model=SavedQuiz, status_code=201)
async def create_quiz(request: StudentQuizGenerateRequest, user: dict = Depends(current_student)):
    for document_id in request.document_ids:
        if not await asyncio.to_thread(teacher_service.student_can_use_document, user["id"], str(document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
    generation_request = request
    decision = None
    if request.adaptive:
        profiles = await asyncio.to_thread(knowledge_profile_service.knowledge_profile, user["id"])
        key = f"practice:{' '.join(request.topic.casefold().split())}"
        profile = next((item for item in profiles["topics"] if item["topic_key"] == key), None)
        status = profile["status"] if profile else "insufficient_evidence"
        decision = {"topic_status": status, **adaptive_learning_service.recommend_difficulty(status, request.difficulty)}
        generation_request = request.model_copy(update={"difficulty": decision["effective_difficulty"]})
    response = await _generate(generate_quiz, generation_request)
    saved = await asyncio.to_thread(student_service.save_quiz, user["id"], request.topic, response)
    return {**saved, "adaptive_decision": decision}


@router.post("/quizzes/personalized", response_model=PersonalizedSavedQuiz, status_code=201)
async def personalized_quiz(request: PersonalizedQuizRequest, user: dict = Depends(current_student)):
    plan = await asyncio.to_thread(personalized_learning_service.personalized_plan, user["id"], request.topic_key)
    if not plan:
        raise HTTPException(status_code=404 if request.topic_key else 422,
                            detail="No available personalized topic found")
    generation = QuizGenerateRequest(topic=plan["topic"], difficulty=plan["difficulty"],
                                     language=request.language, question_count=request.question_count,
                                     question_types=["multiple_choice", "true_false"])
    async def generate_focused(value):
        return await generate_quiz(value, focus_context=plan["focus_context"])
    response = await _generate(generate_focused, generation)
    saved = await asyncio.to_thread(student_service.save_quiz, user["id"], plan["topic"], response, plan["topic_id"])
    return {**saved, "plan": plan}


@router.post("/quizzes/{quiz_id}/attempts", status_code=201)
async def submit_attempt(quiz_id: UUID, request: AttemptRequest, user: dict = Depends(current_student)):
    return await _owned(student_service.submit_attempt, user["id"], str(quiz_id), request)


@router.get("/attempts/{attempt_id}")
async def get_attempt(attempt_id: UUID, user: dict = Depends(current_student)):
    return await _owned(student_service.get_attempt, user["id"], str(attempt_id))


@router.get("/attempts")
async def list_attempts(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0), user: dict = Depends(current_student)):
    return {"attempts": await asyncio.to_thread(student_service.list_attempts, user["id"], limit, offset)}


@router.put("/lessons/{lesson_id}/complete")
async def complete_lesson(lesson_id: UUID, user: dict = Depends(current_student)):
    return await _owned(student_service.complete_lesson, user["id"], str(lesson_id))


@router.get("/lessons")
async def available_lessons(user: dict = Depends(current_student)):
    return {"lessons": await asyncio.to_thread(student_service.available_lessons, user["id"])}


@router.get("/lessons/{lesson_id}")
async def read_lesson(lesson_id: UUID, user: dict = Depends(current_student)):
    return await _owned(student_service.available_lesson, user["id"], str(lesson_id))


@router.post("/study-sessions", status_code=201)
async def start_study(request: StartStudyRequest | None = None, user: dict = Depends(current_student)):
    return await _owned(student_service.start_study, user["id"], str(request.course_id) if request and request.course_id else None)


@router.post("/study-sessions/{session_id}/end")
async def end_study(session_id: UUID, user: dict = Depends(current_student)):
    return await _owned(student_service.end_study, user["id"], str(session_id))


@router.get("/dashboard")
async def dashboard(user: dict = Depends(current_student)):
    return await asyncio.to_thread(student_service.dashboard, user["id"])


@router.get("/knowledge-profile", response_model=KnowledgeProfileResponse)
async def knowledge_profile(user: dict = Depends(current_student)):
    return await asyncio.to_thread(knowledge_profile_service.knowledge_profile, user["id"])


@router.get("/recommendations")
async def recommendations(user: dict = Depends(current_student)):
    return {"recommendations": await asyncio.to_thread(recommendation_service.recommendations, user["id"])}


@router.get("/speech/status")
async def speech_status(user: dict = Depends(current_student)):
    return await asyncio.to_thread(speech_service.status)


@router.post("/speech/synthesize")
async def speech_synthesize(request: SpeechTextRequest, user: dict = Depends(current_student)):
    try:
        audio = await asyncio.to_thread(speech_service.synthesize, request.text)
    except speech_service.SpeechUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return Response(content=audio, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@router.post("/speech/transcribe")
async def speech_transcribe(audio: UploadFile = File(...), user: dict = Depends(current_student)):
    payload = await audio.read(speech_service.MAX_AUDIO_BYTES + 1)
    if len(payload) > speech_service.MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio must be 4 MB or smaller")
    try:
        return await asyncio.to_thread(speech_service.transcribe, payload)
    except speech_service.SpeechUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except speech_service.InvalidAudioError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get("/reviews/due")
async def due_reviews(limit: int = Query(20, ge=1, le=50), user: dict = Depends(current_student)):
    return await asyncio.to_thread(spaced_repetition_service.due_cards, user["id"], limit)


@router.post("/reviews/{card_id}")
async def rate_review(card_id: UUID, request: ReviewRating, user: dict = Depends(current_student)):
    try:
        return await asyncio.to_thread(spaced_repetition_service.review_card, user["id"], str(card_id), request.rating)
    except spaced_repetition_service.CardNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except spaced_repetition_service.CardNotDueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/reviews/{card_id}/history")
async def review_history(card_id: UUID, user: dict = Depends(current_student)):
    try:
        return {"events": await asyncio.to_thread(spaced_repetition_service.review_history, user["id"], str(card_id))}
    except spaced_repetition_service.CardNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/assignments")
async def assignments(user: dict = Depends(current_student)):
    return {"assignments": await asyncio.to_thread(student_service.assigned_quizzes, user["id"])}


@router.get("/courses/{course_id}/materials")
async def course_materials(course_id: UUID, user: dict = Depends(current_student)):
    return {"materials": await _owned(student_service.enrolled_materials, user["id"], str(course_id))}


@router.get("/courses/{course_id}/materials/{material_id}/download")
async def download_material(course_id: UUID, material_id: UUID, user: dict = Depends(current_student)):
    material = await _owned(student_service.enrolled_material, user["id"], str(course_id), str(material_id))
    original_file = DOCUMENT_DIR / f"file{material['document_id']}{Path(material['filename']).suffix.lower()}"
    if not original_file.is_file():
        raise HTTPException(status_code=404, detail="Material file not found")
    return FileResponse(original_file, filename=material["filename"])


async def _student_learning(request, user, operation):
    for document_id in request.document_ids:
        if not await asyncio.to_thread(teacher_service.student_can_use_document, user["id"], str(document_id)):
            raise HTTPException(status_code=404, detail="Document not found")
    return await _generate(operation, request)


@router.post("/learning/generate-lesson", response_model=LessonResponse)
async def student_lesson(request: LearningRequest, user: dict = Depends(current_student)):
    return await _student_learning(request, user, generate_lesson)


@router.post("/learning/generate-flashcards", response_model=SavedFlashcardDeck)
async def student_flashcards(request: FlashcardGenerateRequest, user: dict = Depends(current_student)):
    response = await _student_learning(request, user, generate_flashcards)
    return await asyncio.to_thread(spaced_repetition_service.save_deck, user["id"], request.topic, response)


@router.post("/learning/generate-vocabulary", response_model=VocabularyResponse)
async def student_vocabulary(request: VocabularyGenerateRequest, user: dict = Depends(current_student)):
    return await _student_learning(request, user, generate_vocabulary)
