from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ingest_route import router as ingest_router
from app.routes.chat_route import router as chat_router

from app.core.config import APP_ENV
app = FastAPI() ## main application instance => everything routes, midldlweares must attach to this 


origins = ["https://tube-assist.vercel.app"]

if APP_ENV == "development":
    origins.append("http://localhost:5173")

# ── CORS must be registered BEFORE routers ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"], ## allow get,post
    allow_headers=["*"], ## allow all headers 
)

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
            "backend": ["FastAPI", "LangChain", "Gemini 2.5 Flash", "Gemini Embeddings", "ChromaDB", "Pinecone", "FasterWhisper (Base)", "yt-dlp"],
            "frontend": ["React", "Vite", "Axios"]
        },
        "endpoints": {
            "POST /videos/ingest": "Extract transcript, chunk, embed and store a YouTube video",
            "POST /chat/ask": "Ask a question about an ingested video"
        }
    }

## registering external routes 
app.include_router(ingest_router)
app.include_router(chat_router)