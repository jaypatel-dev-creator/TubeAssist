from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import (
    TubeAssistException,
    tubeassist_exception_handler,
    generic_exception_handler,
)
from app.routes.ingest_route import router as ingest_router
from app.routes.chat_route import router as chat_router
from app.routes.health_route import router as health_router
from app.services.embedding_service import init_embedding_model
from app.services.vector_store_service import init_vector_store
from app.services.rag_service import init_rag_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    init_embedding_model()
    init_vector_store()
    init_rag_service()
    yield
    # ── Shutdown ───────────────────────────────────────────────────────────────


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="TubeAssist",
        description="AI-powered YouTube video assistant",
        version="1.0.0",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # ── Exception handlers ─────────────────────────────────────────────────────
    app.add_exception_handler(TubeAssistException, tubeassist_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    origins = ["https://tube-assist.vercel.app"]
    if settings.app_env == "development":
        origins.append("http://localhost:5173")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(chat_router)

    return app


app = create_app()


@app.get("/")
def root():
    return {"message": "Welcome to TubeAssist API"}


@app.get("/about")
def about():
    return {
        "project": "TubeAssist",
        "version": "1.0",
        "description": "AI-powered YouTube video assistant. Paste a video URL, ask questions, and get answers grounded in the video transcript using RAG.",
        "features": [
            "YouTube caption extraction via yt-dlp",
            "FasterWhisper fallback transcription for videos without captions",
            "Recursive text chunking with overlap (1000 chars / 200 overlap)",
            "Gemini text embeddings (embedding-001, 3072 dimensions)",
            "ChromaDB (local) and Pinecone (production) vector storage",
            "Scoped retrieval via video_id metadata filtering",
            "Two-stage relevance filtering — score threshold + LLM-as-a-Judge",
            "LLM fallback to general knowledge when no relevant context found",
            "Conversation memory across follow-up questions (last 5 turns)",
            "Environment-based configuration — Chroma locally, Pinecone in production"
        ],
        "tech_stack": {
            "backend": ["FastAPI", "LangChain", "Gemini 3.1 Flash-Lite", "Gemini Embeddings", "ChromaDB", "Pinecone", "FasterWhisper (Base)", "yt-dlp"],
            "frontend": ["React", "Vite", "Axios"]
        },
        "endpoints": {
            "POST /videos/ingest": "Extract transcript, chunk, embed and store a YouTube video",
            "POST /chat/ask": "Ask a question about an ingested video"
        }
    }