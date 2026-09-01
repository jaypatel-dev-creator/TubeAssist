# TubeAssist 🎬

> AI-powered YouTube video assistant — ask questions about any YouTube video using a full RAG pipeline with session-based conversational memory.

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

TubeAssist lets you paste any YouTube URL and instantly start asking questions about the video — powered by a full RAG pipeline. The system fetches the video transcript via yt-dlp (with Groq Whisper API as fallback), chunks it recursively, converts chunks into vector embeddings using Gemini Embeddings, stores them in ChromaDB (locally) or Pinecone (production), and retrieves the most relevant context to answer your questions using Gemini 3.1 Flash Lite.

Each video load generates a unique session ID — all follow-up questions within that session carry conversation history, enabling natural multi-turn dialogue. If a question is unrelated to the video, the system falls back to general LLM knowledge — clearly indicated to the user with a badge in the chat UI.

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
│   Groq Whisper        TextSplitter)      │
│   API fallback)          │               │
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
│  User Question + session_id              │
│       → history fetched from             │
│         _session_store[session_id]       │
│       → retriever_service                │
│         (similarity search,              │
│          video_id filter)                │
│                  │                       │
│      Stage 1 — Score filter              │
│      Stage 2 — LLM-as-a-Judge            │
│          ├── relevant → RAG answer       │
│          └── irrelevant → LLM fallback   │
│                  │                       │
│                  ▼                       │
│          rag_service                     │
│       (history + context +               │
│        Gemini 3.1 Flash Lite)            │
│                  │                       │
│      Q+A appended to session history     │
└──────────────────────────────────────────┘
```

---

## Advanced RAG Techniques

| Technique | Implementation |
|---|---|
| Metadata filtering | `filter={\"video_id\": video_id}` — scoped retrieval per video |
| Two-stage relevance filtering | Score threshold (0.7) + LLM-as-a-Judge |
| LLM-as-a-Judge | `NO_RELEVANT_CONTEXT` pattern — LLM self-evaluates context relevance |
| LLM fallback | General knowledge answer when no relevant context found |
| Session-based STM | Per-session history window (last 6 messages) injected into every prompt |

### Two-Stage Relevance Filtering

**Stage 1 — Score filter (fast, no LLM call):**
Chunks filtered by cosine distance threshold (`0.7`). Chunks that don't pass trigger LLM fallback immediately — no wasted LLM call.

**Stage 2 — LLM-as-a-Judge (semantic, accurate):**
Even if chunks pass the score filter, Gemini is instructed to return sentinel string `"NO_RELEVANT_CONTEXT"` if the retrieved context doesn't actually answer the question. Catches subtle irrelevance that pure distance metrics miss.

Both stages route to the same `_llm_fallback()` — answering from general knowledge and returning `from_video: false` to the frontend.

### Session-Based Conversational Memory

Each video load generates a `session_id` (UUID) on the frontend. Every subsequent question carries this ID to the backend, which maintains an in-memory session store (`dict[str, list[dict]]`). The last 6 messages (3 user + 3 AI turns) are injected into both the RAG prompt and the fallback prompt — enabling natural follow-up questions without repeating context. Memory is non-persistent by design: it lives in process memory and resets on server restart.

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
| Groq Whisper API (whisper-large-v3-turbo) | Fallback audio transcription |
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
- Groq API key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in GEMINI_API_KEY and GROQ_API_KEY
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
| `GROQ_API_KEY` | Yes | — | Groq API key for Whisper fallback |
| `APP_ENV` | No | `development` | Controls Swagger UI visibility and log level |
| `VECTOR_STORE` | No | `chroma` | `chroma` locally, `pinecone` in production |
| `PINECONE_API_KEY` | Pinecone only | — | Pinecone API key |
| `PINECONE_INDEX` | Pinecone only | `tubeassist` | Pinecone index name |

### `frontend/.env` (local only — never committed)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | No | `http://localhost:8000` | FastAPI backend URL |

---

## Configuration

Config is managed via `pydantic-settings` `BaseSettings` — validated at startup, not scattered `os.getenv()` calls. If `GEMINI_API_KEY` or `GROQ_API_KEY` is missing, the server refuses to start with a clear validation error rather than failing silently mid-request.

**Local dev:**
```bash
uvicorn app.main:app --reload
# reads .env → uses ChromaDB → Swagger UI at /docs → DEBUG log level
```

**Production (Render):**
Set all vars directly in Render dashboard — no `.env` files needed. `pydantic-settings` reads from environment directly.
```
GEMINI_API_KEY=your_key
GROQ_API_KEY=your_key
APP_ENV=production
VECTOR_STORE=pinecone
PINECONE_API_KEY=your_key
PINECONE_INDEX=tubeassist
```

---

## Deployment

**Backend → Render**
Push to GitHub → Render auto-deploys via `render.yaml`. Set `GEMINI_API_KEY`, `GROQ_API_KEY`, and `PINECONE_API_KEY` manually in Render dashboard (secrets). Everything else is handled by `render.yaml`.

**Frontend → Vercel**
Connect GitHub repo to Vercel. Set `VITE_API_URL=https://your-render-url.com` in Vercel dashboard → Environment Variables. Vite bakes it into the bundle at deploy time.

---

## Key Design Decisions

**Why module-level singletons over FastAPI DI?** FastAPI's `Depends()` chain was designed for per-request resources like DB sessions — not for wiring service graphs. Expensive objects (LLM client, embedding model, vector store) are initialized once in `lifespan()` as module-level singletons and accessed directly. `Depends()` has no role in this codebase because there are no per-request resources to inject.

**Why typed exceptions over return dicts?** The original design returned `{"status": "error", ...}` with HTTP 200 — meaning API clients couldn't use status codes to detect failures. A typed exception hierarchy (`TubeAssistException` subclasses) with global handlers ensures every error maps to the correct HTTP status code (422, 409, 500) with a consistent `{"error": "..."}` response shape.

**Why two-stage filtering over one?** Score filter alone can't detect semantic irrelevance — a chunk can be mathematically close but contextually wrong. LLM judge alone without pre-filtering wastes tokens on garbage chunks. Together: Stage 1 narrows candidates cheaply, Stage 2 makes the final semantic call.

**Why Groq Whisper API over local Whisper?** Running faster-whisper locally requires ctranslate2 — a heavy compiled C++ dependency that bloats the build and exceeds Render's free tier limits. Groq's hosted `whisper-large-v3-turbo` runs on their LPU hardware, eliminates the local model entirely, and delivers faster transcription with equal or better accuracy.

**Why 64kbps mp3 for audio download?** Groq's free tier Whisper endpoint has a 25MB file size limit. Forcing yt-dlp to download at 64kbps mp3 keeps audio at ~28MB/hour — videos up to ~50 minutes stay safely under the limit. A 24MB size guard runs after download as a safety net: if the file still exceeds the threshold, it's deleted and a clear error is returned to the user before the Groq call is ever made.

**Why Pinecone for production?** ChromaDB is embedded and writes to disk. Render's free tier has ephemeral storage that wipes on every deploy. Pinecone is cloud-hosted and persistent across restarts and redeployments.

**Why yt-dlp over youtube-transcript-api?** yt-dlp handles both caption extraction and metadata in one library, supports more video formats, and is actively maintained.

**Why in-process dict for STM over Redis?** The requirement is non-persistent, single-server conversational memory scoped to a video session. An in-process `dict[str, list[dict]]` is zero-dependency, zero-latency, and matches the requirement exactly. Redis adds operational complexity (another service to provision, connect, and monitor) for no functional gain at this scale. The session store is intentionally simple — it resets on restart, which is the desired behaviour.

**Why a dedicated `core/logging.py`?** Centralising `setup_logging()` and `get_logger()` in one module means every service file does a single import instead of configuring `logging.basicConfig()` inline or at module level. Log level is environment-driven (`DEBUG` in development, `INFO` in production) without any file touching `APP_ENV` directly.

---

## ⚠️ Known Limitations & Infrastructure Notes

### YouTube Transcript Fetch — Render Deployment
**Status:** Blocked in production
**Root cause:** Render runs on AWS datacenter IPs. YouTube blanket-blocks datacenter IP ranges for yt-dlp requests — including the Whisper audio fallback, which also uses yt-dlp for audio download. Residential IPs work fine; the issue is *who* makes the request, not the code itself.
**Verified locally:** Both transcript fetch and Whisper fallback work perfectly on local/residential IPs.
**Production fix:** Paid transcript API (Supadata, RapidAPI) or residential proxy service. Documented as a known infrastructure limitation.

### STM — Non-Persistent by Design
Session history lives in process memory. Server restart clears all sessions. This is intentional — no persistence requirement exists. Redis or a database-backed store is a straightforward upgrade path if persistence is needed.

### Groq Whisper — Video Length
Groq's free tier Whisper endpoint has a 25MB file size limit. Audio is downloaded at 64kbps mp3, keeping videos up to ~50 minutes safely under the limit. Videos beyond that trigger a clean 422 error with a clear message to the user.

### Multilingual Content
yt-dlp fetches captions in whatever language is available — it does not filter by language. If a video has only Hindi captions, those are stored as-is and an English question will return `from_video: false` — embeddings won't align across languages, Stage 1 score filter fails, and the LLM fallback is triggered. Translation before chunking is a known gap, planned for a future iteration.

### Cold Start
Backend deployed on Render free tier — expect 50–60 second cold start after inactivity.

---

## Roadmap
Streaming responses and persistent cross-session memory planned for a future iteration.