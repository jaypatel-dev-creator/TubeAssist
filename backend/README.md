# TubeAssist — Backend

FastAPI backend implementing a full RAG pipeline over YouTube video transcripts. Accepts a video URL, extracts and indexes the transcript, then answers natural language questions using retrieved context with two-stage relevance filtering, session-based conversational memory, and LLM fallback.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| FastAPI + Uvicorn | REST API, ASGI server |
| LangChain | RAG orchestration, prompt templates |
| ChromaDB | Local vector store |
| Pinecone | Cloud vector store (production) |
| Gemini 3.1 Flash-Lite  | LLM for answer generation |
| Gemini Embeddings | Text → vector conversion (3072 dimensions) |
| yt-dlp | Primary transcript extraction + video metadata |
| Groq Whisper API (whisper-large-v3-turbo) | Fallback audio transcription |
| Pydantic + pydantic-settings | Request/response validation + config management |

---

## Backend Structure
```
backend/
├── app/
│   ├── core/
│   │   ├── config.py                 # pydantic-settings BaseSettings + get_settings()
│   │   ├── exceptions.py             # typed exception hierarchy + global handlers
│   │   └── logging.py                # setup_logging() + get_logger() — centralised logging config
│   ├── routes/
│   │   ├── health_route.py           # GET /health
│   │   ├── ingest_route.py           # POST /videos/ingest
│   │   └── chat_route.py             # POST /chat/ask
│   ├── schemas/
│   │   ├── ingest_schema.py          # VideoIngestRequest, VideoIngestSuccess
│   │   └── chat_schema.py            # ChatRequest (incl. session_id), ChatResponse, ChunkMetadata
│   ├── services/
│   │   ├── providers/
│   │   │   ├── youtube_provider.py   # yt-dlp caption extraction
│   │   │   ├── whisper_provider.py   # Groq Whisper API fallback
│   │   │   └── metadata_provider.py  # video title, author via yt-dlp
│   │   ├── transcript_service.py     # transcript orchestration
│   │   ├── chunking_service.py       # RecursiveCharacterTextSplitter singleton
│   │   ├── embedding_service.py      # Gemini embeddings singleton
│   │   ├── vector_store_service.py   # ChromaDB / Pinecone singleton
│   │   ├── retriever_service.py      # similarity search + score normalization
│   │   ├── ingestion_service.py      # ingestion orchestrator
│   │   └── rag_service.py            # RAG + STM session store + LLM fallback
│   └── main.py                       # FastAPI app + lifespan + exception handlers
├── .env.example
├── render.yaml
└── requirements.txt
```

---

## RAG Pipeline

### Phase 1 — Ingestion
```
YouTube URL
│
├─► extract_video_id()                        # regex extraction
│         │
│         ├─► yt-dlp                          # primary transcript extraction
│         └─► Groq Whisper API                # fallback transcript extraction
│
├─► metadata_provider                         # title, author via yt-dlp
│
├─► video_exists()                            # duplicate ingestion guard
│
├─► create_chunks()                           # RecursiveCharacterTextSplitter
│         chunk_size=1000, chunk_overlap=200
│         metadata: video_id, title, author, chunk_index
│
└─► add_documents()                           # embed + persist
          ChromaDB (local) / Pinecone (prod)
```

### Phase 2 — Query
```
User Question + session_id
│
├─► _get_history(session_id)
│         last 6 messages fetched from _session_store[session_id]
│         (windowed to 3 user + 3 AI turns)
│
├─► retrieve_with_scores()
│         k=6, filter={"video_id": video_id}
│         score normalized to distance scale for both backends
│
├─► Stage 1 — Score filter (threshold = 0.7)
│         ├── chunks pass → continue to Stage 2
│         └── no chunks pass → LLM fallback → from_video: false
│
├─► Stage 2 — LLM-as-a-Judge
│         ├── context relevant → RAG answer → from_video: true
│         └── LLM returns "NO_RELEVANT_CONTEXT" → LLM fallback → from_video: false
│
├─► ChatPromptTemplate
│         system + context + history + question
│
├─► Gemini 3.1 Flash-Lite (temperature=0.3)
│
└─► _append_to_history(session_id, question, answer)
          Q+A pair written back to _session_store[session_id]
```

---

## API Reference

### `GET /health`

```json
{ "status": "ok", "service": "tubeassist" }
```

---

### `POST /videos/ingest`

**Request**
```json
{ "url": "https://www.youtube.com/watch?v=VIDEO_ID" }
```

**Response — success**
```json
{
  "status": "success",
  "video_id": "VIDEO_ID",
  "video_title": "Video Title Here",
  "video_author": "Video Author Here",
  "chunks_stored": 42
}
```

**Error responses**

| Status | Condition |
|---|---|
| `422` | Invalid YouTube URL or transcript fetch failed |
| `409` | Video already indexed |
| `500` | Vector store failure |

All errors return `{ "error": "..." }`. The `409` response also includes `video_id`, `video_title`, and `video_author` so the client can unlock chat without re-ingesting.

```json
{
  "error": "'Video Title' is already indexed.",
  "video_id": "VIDEO_ID",
  "video_title": "Video Title",
  "video_author": "Author"
}
```

---

### `POST /chat/ask`

**Request**
```json
{
  "question": "What is self-attention?",
  "video_id": "VIDEO_ID",
  "session_id": "uuid-generated-per-video-load"
}
```

`session_id` is optional — if omitted, the request is treated as stateless with no history.

**Response**
```json
{
  "answer": "Self-attention is a mechanism that...",
  "sources": [{ "video_id": "...", "chunk_index": 3, "title": "...", "author": "..." }],
  "from_video": true
}
```

`from_video: false` when answer comes from general LLM knowledge — no relevant context found in video.

---

## Key Implementation Details

**Module-level singletons + lifespan init** — expensive objects (embedding model, vector store, LLM client, prompts) are initialized once at startup via `lifespan()` and accessed as module-level singletons. No FastAPI DI chain — `Depends()` has no role here since there are no per-request resources to inject.

**Session-based STM** — `rag_service.py` maintains a module-level `_session_store: dict[str, list[dict]] = {}`. The dict itself is a singleton; each value is an isolated list per `session_id`. Every `ask()` call fetches the last 6 messages for that session (window of 3 turns), injects them into the prompt as formatted `User: / Assistant:` history, then appends the new Q+A pair after the LLM responds. Both the RAG prompt and the general fallback prompt receive history — follow-up questions work regardless of whether the answer came from the video or general knowledge. Memory is non-persistent: it resets on server restart by design.

**Typed exception hierarchy** — `TubeAssistException` base class with domain subclasses (`InvalidURLException`, `TranscriptFetchException`, `VideoAlreadyIndexedException`, `VectorStoreException`, `RAGException`). Two global handlers in `main.py` ensure every error returns the correct HTTP status code with a consistent `{"error": "..."}` shape. Routes contain zero try/except. Internal error details (raw API errors, stack traces) are logged server-side only — never exposed to the client.

**Centralised logging** — `core/logging.py` owns `setup_logging(app_env)` and `get_logger(name)`. Called once in `lifespan()` with `settings.app_env` — `DEBUG` in development, `INFO` in production. Every service file calls `get_logger(__name__)` for a named logger. Noisy third-party loggers (`httpx`, `httpcore`, `chromadb`, `google.auth`, etc.) are suppressed to `WARNING`.

**Pydantic-settings config** — `BaseSettings` with `get_settings()` + `@lru_cache`. Validated at startup — missing `GEMINI_API_KEY` or `GROQ_API_KEY` refuses server start immediately rather than failing mid-request.

**Two-stage relevance filtering** — Stage 1 applies cosine distance threshold (0.7) to filter mathematically irrelevant chunks. Stage 2 uses LLM-as-a-Judge — model returns `"NO_RELEVANT_CONTEXT"` if chunks don't actually answer the question. Both stages trigger the same `_llm_fallback()`.

**Dual transcript strategy** — yt-dlp attempted first (fast, no compute). Empty or missing captions trigger Groq Whisper API fallback — audio downloaded via yt-dlp at 64kbps mp3, transcribed via Groq's hosted `whisper-large-v3-turbo`. 64kbps keeps audio at ~28MB/hour, staying safely under Groq's 25MB free tier limit for videos up to ~50 minutes. A 24MB size guard runs post-download as a safety net — if the file still exceeds the threshold, it is deleted and a clean 422 is returned before the Groq call is made.

**Chunking strategy** — `RecursiveCharacterTextSplitter` with `chunk_size=1000` and `chunk_overlap=200`. Splits on natural boundaries (paragraphs → sentences → words). Each chunk carries `video_id`, `title`, `author`, `chunk_index` metadata.

**Score normalization** — ChromaDB returns distance (lower = more relevant), Pinecone returns similarity (higher = more relevant). Pinecone scores normalized via `1 - score` so both backends share the same `0.7` threshold.

**Temperature=0.3** — low temperature keeps answers grounded in retrieved context. Higher values risk creative drift from source material.

**Gemini 3+ content normalization** — `extract_text_content()` normalizes `response.content` which returns a list of parts in Gemini 3+ models instead of a plain string. Handles both formats so the pipeline works across model generations.

---

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# fill in GEMINI_API_KEY and GROQ_API_KEY in .env
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

---

## Testing

Integration testing via Swagger UI (`http://localhost:8000/docs`):

`POST /videos/ingest` edge cases:
- Valid URL → successful ingestion, `chunks_stored` returned
- Same URL twice → `409 already indexed`
- Invalid URL → `422` with clear error message
- Video without captions → Groq Whisper API fallback triggered
- Video over ~50 minutes → `422` with clear file size error message

`POST /chat/ask` edge cases:
- Relevant question → grounded answer, `from_video: true`
- Irrelevant question → LLM fallback, `from_video: false`
- Follow-up question (same `session_id`) → history injected, context-aware answer
- Fresh `session_id` on same `video_id` → clean history, no bleed from prior session

---

## Key Learnings

- **RAG Pipeline Design** — full ingestion + retrieval pipeline: transcript extraction → recursive chunking → vector embeddings → similarity retrieval → grounded LLM generation with fallback
- **Advanced RAG** — two-stage relevance filtering (score threshold + LLM-as-a-Judge) and metadata filtering for scoped per-video retrieval
- **Session-Based STM** — in-process `dict[str, list[dict]]` keyed by `session_id`; windowed history injected into every prompt; isolated per session with no cross-contamination
- **Vector Database & Score Normalization** — handled backend-specific score scales (Chroma distance vs Pinecone similarity) with `1 - score` normalization for a unified threshold
- **Pydantic-Settings Config** — `BaseSettings` with `@lru_cache` for validated, type-safe config as a singleton — replaces scattered `os.getenv()` calls
- **Module-Level Singletons** — production FastAPI pattern: expensive resources initialized once in `lifespan()`, accessed directly in services — no DI chain needed
- **Typed Exception Hierarchy** — base exception + domain subclasses + global handlers: routes stay clean, errors always return correct HTTP status codes, internals never leak to clients
- **Centralised Logging** — `core/logging.py` pattern: `setup_logging()` + `get_logger(__name__)` per file; environment-driven log level; third-party loggers suppressed
- **Dual Transcript Strategy** — yt-dlp primary with Groq Whisper API fallback; 64kbps bitrate cap + 24MB size guard handle Groq's free tier file size constraint cleanly