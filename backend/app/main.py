import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.lan_access import AuthRateLimit, LanAccessGate, SecurityHeaders
from app.api.chat import router as chat_router
from app.api.documents import router as document_router
from app.api.rag_memory import router as rag_memory_router
from app.api.learning_content import router as learning_content_router
from app.api.learning_tools import router as learning_tools_router
from app.api.student import router as student_router
from app.api.teacher import router as teacher_router
from app.services.ollama_service import get_ollama_status


app = FastAPI(
    title = "Offline AI learning API",
    description="Local AI learning assistant powered by ollama.",
    version="1.0.0",
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.get("/api/ollama/status")
async def ollama_status():
    return await get_ollama_status()

app.include_router(
    chat_router,
    prefix="/api",
    tags=["Chat"],
)

app.include_router(
    document_router,
    prefix="/api/documents"
)

app.include_router(rag_memory_router)
app.include_router(learning_content_router)
app.include_router(learning_tools_router)
app.include_router(student_router)
app.include_router(teacher_router)

# Serve the built React app and API from one origin in desktop/LAN mode.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {"message": "Offline AI learning API is running"}

app.add_middleware(AuthRateLimit)
lan_password = os.environ.get("LAN_ACCESS_PASSWORD", "")
if lan_password:
    if len(lan_password) < 12:
        raise ValueError("LAN_ACCESS_PASSWORD must contain at least 12 characters")
    app.add_middleware(LanAccessGate, password=lan_password)
    app.add_middleware(SecurityHeaders)
