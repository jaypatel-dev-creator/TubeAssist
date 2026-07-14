# TubeAssist 🎬

> AI-powered YouTube video assistant — ask questions about any YouTube video using a full RAG pipeline.

---

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C?style=flat)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Local-FF6B35?style=flat)
![Pinecone](https://img.shields.io/badge/Pinecone-Production-00B388?style=flat)
![Gemini](https://img.shields.io/badge/Gemini-3.1_Flash_Lite-4285F4?style=flat&logo=google&logoColor=white)

---

![TubeAssist Demo](assets/demo.gif)

---

## What is TubeAssist?

TubeAssist lets you paste any YouTube URL and instantly start asking questions about the video — powered by a full RAG pipeline. The system fetches the video transcript via yt-dlp (with FasterWhisper as fallback), chunks it recursively, converts chunks into vector embeddings using Gemini Embeddings, stores them in ChromaDB (locally) or Pinecone (production), and retrieves the most relevant context to answer your questions using Gemini 3.1 Flash Lite.

If a question is unrelated to the video, the system falls back to general LLM knowledge — clearly indicated to the user with a badge in the chat UI.

---

## Architecture

```
YouTube URL
     │
     ▼
┌──────────────────────────────────────────┐
│           INGESTION PIPELINE             │
│                                          │
│  transcript_service → chunking_service   │
│  (yt-dlp primary,    (RecursiveCharacter │
│   Whisper fallback)   TextSplitter)      │
│                          │               │
│                          ▼               │
│                 embedding_service        │
│                 (Gemini Embeddings)      │
│                          │               │
│                          ▼               │
│                 vector_store_service     │
│                 (ChromaDB / Pinecone)    │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│           RAG QUERY PIPELINE             │
│                                          │
│  User Question → retriever_service       │
│                  (similarity search,     │
│                   video_id filter)       │
│                          │               │
│              Stage 1 — Score filter      │
│              Stage 2 — LLM-as-a-Judge    │
│                  ├── relevant → RAG      │
│                  └── irrelevant → LLM    │
│                          fallback        │
│                          │               │
│                          ▼               │
│                  rag_service             │
│               (context +                 │
│                + Gemini 3.1 Flash Lite ) │
└──────────────────────────────────────────┘
```

---

## Advanced RAG Techniques

| Technique | Implementation |
|---|---|
| Metadata filtering | `filter={"video_id": video_id}` — scoped retrieval per video |
| Two-stage relevance filtering | Score threshold (0.7) + LLM-as-a-Judge |
| LLM-as-a-Judge | `NO_RELEVANT_CONTEXT` pattern — LLM self-evaluates context relevance |
| LLM fallback | General knowledge answer when no relevant context found |

### Two-Stage Relevance Filtering

**Stage 1 — Score filter (fast, no LLM call):**
Chunks filtered by cosine distance threshold (`0.7`). Chunks that don't pass trigger LLM fallback immediately — no wasted LLM call.

**Stage 2 — LLM-as-a-Judge (semantic, accurate):**
Even if chunks pass the score filter, Gemini is instructed to return sentinel string `"NO_RELEVANT_CONTEXT"` if the retrieved context doesn't actually answer the question. Catches subtle irrelevance that pure distance metrics miss.

Both stages route to the same `_llm_fallback()` — answering from general knowledge and returning `from_video: false` to the frontend.

---

## Tech Stack

### Backend
| Technology | Role |
|---|---|
| FastAPI + Uvicorn | REST API, ASGI server |
| LangChain | RAG orchestration, prompt templates |
| ChromaDB | Local vector database |
| Pinecone | Cloud vector database (production) |
| Gemini 3.1 Flash-Lite | LLM for answer generation |
| Gemini Embeddings | Text → vector conversion (3072 dimensions) |
| yt-dlp | Primary transcript + metadata extraction |
| FasterWhisper (base) | Fallback audio transcription (lazy loaded) |
| Pydantic + pydantic-settings | Request/response validation + config management |

### Frontend
| Technology | Role |
|---|---|
| React 18 + Vite | UI framework + build tool |
| Axios | HTTP client |

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+
- Google Gemini API key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in GEMINI_API_KEY
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_URL=http://localhost:8000
npm run dev
# App at http://localhost:5173
```

---

## Environment Variables

### `backend/.env` (local only — never committed)

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `APP_ENV` | No | `development` | controls Swagger UI visibility and CORS origins |
| `VECTOR_STORE` | No | `chroma` | `chroma` locally, `pinecone` in production |
| `PINECONE_API_KEY` | Pinecone only | — | Pinecone API key |
| `PINECONE_INDEX` | Pinecone only | `tubeassist` | Pinecone index name |

### `frontend/.env` (local only — never committed)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | No | `http://localhost:8000` | FastAPI backend URL |

---

## Configuration

Config is managed via `pydantic-settings` `BaseSettings` — validated at startup, not scattered `os.getenv()` calls. If `GEMINI_API_KEY` is missing, the server refuses to start with a clear validation error rather than failing silently mid-request.

**Local dev:**
```bash
uvicorn app.main:app --reload
# reads .env → uses ChromaDB → Swagger UI at /docs
```

**Production (Render):**
Set all vars directly in Render dashboard — no `.env` files needed. `pydantic-settings` reads from environment directly.
```
GEMINI_API_KEY=your_key
APP_ENV=production
VECTOR_STORE=pinecone
PINECONE_API_KEY=your_key
PINECONE_INDEX=tubeassist
```

---

## Deployment

**Backend → Render**
Push to GitHub → Render auto-deploys via `render.yaml`. Set `GEMINI_API_KEY` and `PINECONE_API_KEY` manually in Render dashboard (secrets). Everything else is handled by `render.yaml`.

**Frontend → Vercel**
Connect GitHub repo to Vercel. Set `VITE_API_URL=https://your-render-url.com` in Vercel dashboard → Environment Variables. Vite bakes it into the bundle at deploy time.

---

## Key Design Decisions

**Why module-level singletons over FastAPI DI?** FastAPI's `Depends()` chain was designed for per-request resources like DB sessions — not for wiring service graphs. Expensive objects (LLM client, embedding model, vector store) are initialized once in `lifespan()` as module-level singletons and accessed directly. `Depends()` has no role in this codebase because there are no per-request resources to inject.

**Why typed exceptions over return dicts?** The original design returned `{"status": "error", ...}` with HTTP 200 — meaning API clients couldn't use status codes to detect failures. A typed exception hierarchy (`TubeAssistException` subclasses) with global handlers ensures every error maps to the correct HTTP status code (422, 409, 500) with a consistent `{"error": "..."}` response shape.

**Why two-stage filtering over one?** Score filter alone can't detect semantic irrelevance — a chunk can be mathematically close but contextually wrong. LLM judge alone without pre-filtering wastes tokens on garbage chunks. Together: Stage 1 narrows candidates cheaply, Stage 2 makes the final semantic call.

**Why lazy Whisper loading?** FasterWhisper base model requires ~600MB RAM. Loading at startup on Render's free tier (512MB) causes OOM crashes. Lazy loading means it only loads when a video has no captions — most tech and educational videos have auto-generated captions, so Whisper rarely fires in practice.

**Why Pinecone for production?** ChromaDB is embedded and writes to disk. Render's free tier has ephemeral storage that wipes on every deploy. Pinecone is cloud-hosted and persistent across restarts and redeployments.

**Why yt-dlp over youtube-transcript-api?** yt-dlp handles both caption extraction and metadata in one library, supports more video formats, and is actively maintained.

---

## ⚠️ Known Limitations & Infrastructure Notes

### YouTube Transcript Fetch — Render Deployment
**Status:** Blocked in production  
**Root cause:** Render runs on AWS datacenter IPs. YouTube blanket-blocks
datacenter IP ranges for yt-dlp requests — including the Whisper audio
fallback, which also uses yt-dlp for audio download. Residential IPs work
fine; the issue is *who* makes the request, not the code itself.  
**Verified locally:** Both transcript fetch and Whisper fallback work
perfectly on local/residential IPs.  
**Production fix:** Paid transcript API (Supadata, RapidAPI) or residential
proxy service. Documented as a known infrastructure limitation.

### Cold Start
Backend deployed on Render free tier — expect 50–60 second cold start after inactivity.

---

## Roadmap
Session-based conversation memory (Redis) and streaming responses planned for v2.