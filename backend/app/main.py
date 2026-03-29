from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ingest_route import router as ingest_router
from app.routes.chat_route import router as chat_router

app = FastAPI() ## main application instance => everything routes, midldlweares must attach to this 

# ── CORS must be registered BEFORE routers ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], ## react runs on 5173
    allow_methods=["*"], # allow get, put , post , delete
    allow_headers=["*"], # allow all headers 
)

# ── Routers registered AFTER middleware ──
## default router/ endpoint 
@app.get("/")
def root():
    return {"message": "Welcome to TubeAssist API"}

## about endpoint 
@app.get("/about")
def about():
    return {
        "project": "TubeAssist",
        "description": "AI-powered assistant that allows users to ask questions about YouTube videos using Retrieval-Augmented Generation (RAG).",
        "features": [
            "YouTube caption extraction via yt-dlp",
            "FasterWhisper fallback transcription",
            "Recursive chunking with overlap",
            "Gemini vector embeddings",
            "ChromaDB vector storage with video_id metadata filtering",
            "Conversation memory across turns",
            "Grounded answer generation"
        ],
        "tech_stack": [
            "FastAPI",
            "LangChain",
            "ChromaDB",
            "Gemini 2.5 Flash",
            "Gemini Embeddings",
            "FasterWhisper(Base)",
            "yt-dlp",
            "React (frontend)"
        ],
        "version": "1.0"
    }


## registering external routes 
app.include_router(ingest_router)
app.include_router(chat_router)