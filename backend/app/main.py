from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as document_router
from app.api.rag_memory import router as rag_memory_router
from app.api.learning_content import router as learning_content_router
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

@app.get("/")
async def root():
    return{
        "message":  "Offile AI learning API is running"
    }
    
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
