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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
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