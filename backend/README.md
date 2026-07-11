# TubeAssist — Backend

FastAPI backend implementing a full RAG pipeline over YouTube video transcripts. Accepts a video URL, extracts and indexes the transcript, then answers natural language questions using retrieved context with two-stage relevance filtering and LLM fallback.

---

## Tech Stack

| Technology | Purpose |
|---|---|
| FastAPI + Uvicorn | REST API, ASGI server |
| LangChain | RAG orchestration, prompt templates, memory |
| ChromaDB | Local vector store |
| Pinecone | Cloud vector store (production) |
| Gemini 2.5 Flash | LLM for answer generation |
| Gemini Embeddings | Text → vector conversion (3072 dimensions) |
| yt-dlp | Primary transcript extraction + video metadata |
| FasterWhisper | Fallback audio transcription (lazy loaded) |
| Pydantic + pydantic-settings | Request/response validation + config management |

---

## Backend Structure
```
backend/
├── app/
│   ├── core/
│   │   ├── config.py                 # pydantic-settings BaseSettings + get_settings()
│   │   └── exceptions.py             # typed exception hierarchy + global handlers
│   ├── routes/
│   │   ├── health_route.py           # GET /health
│   │   ├── ingest_route.py           # POST /videos/ingest
│   │   └── chat_route.py             # POST /chat/ask
│   ├── schemas/
│   │   ├── ingest_schema.py          # VideoIngestRequest, VideoIngestSuccess
│   │   └── chat_schema.py            # ChatRequest, ChatResponse, ChunkMetadata
│   ├── services/
│   │   ├── providers/
│   │   │   ├── youtube_provider.py   # yt-dlp caption extraction
│   │   │   ├── whisper_provider.py   # FasterWhisper fallback (lazy loaded)
│   │   │   └── metadata_provider.py  # video title, author via yt-dlp
│   │   ├── transcript_service.py     # transcript orchestration
│   │   ├── chunking_service.py       # RecursiveCharacterTextSplitter singleton
│   │   ├── embedding_service.py      # Gemini embeddings singleton
│   │   ├── vector_store_service.py   # ChromaDB / Pinecone singleton
│   │   ├── retriever_service.py      # similarity search + score normalization
│   │   ├── ingestion_service.py      # ingestion orchestrator
│   │   └── rag_service.py            # RAG + LLM fallback + memory
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
│         └─► FasterWhisper                   # fallback transcript extraction
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
User Question
│
├─► _build_memory()                           # fresh ConversationBufferWindowMemory (k=5)
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
│         system + MessagesPlaceholder + context + question
│
├─► Gemini 2.5 Flash (temperature=0.3)
│
└─► memory.save_context()                     # persist turn
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

All errors return `{ "error": "..." }`.

---

### `POST /chat/ask`

**Request**
```json
{
  "question": "What is self-attention?",
  "video_id": "VIDEO_ID"
}
```

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

**Typed exception hierarchy** — `TubeAssistException` base class with domain subclasses (`InvalidURLException`, `TranscriptFetchException`, `VideoAlreadyIndexedException`, `VectorStoreException`, `RAGException`). Two global handlers in `main.py` ensure every error returns the correct HTTP status code with a consistent `{"error": "..."}` shape. Routes contain zero try/except.

**Pydantic-settings config** — `BaseSettings` with `get_settings()` + `@lru_cache`. Validated at startup — missing `GEMINI_API_KEY` refuses server start immediately rather than failing mid-request.

**Two-stage relevance filtering** — Stage 1 applies cosine distance threshold (0.7) to filter mathematically irrelevant chunks. Stage 2 uses LLM-as-a-Judge — model returns `"NO_RELEVANT_CONTEXT"` if chunks don't actually answer the question. Both stages trigger the same `_llm_fallback()`.

**Dual transcript strategy** — yt-dlp attempted first (fast, no compute). Empty or missing captions trigger FasterWhisper fallback. Whisper model loads lazily — only when needed — keeping RAM low on free-tier deployment.

**Chunking strategy** — `RecursiveCharacterTextSplitter` with `chunk_size=1000` and `chunk_overlap=200`. Splits on natural boundaries (paragraphs → sentences → words). Each chunk carries `video_id`, `title`, `author`, `chunk_index` metadata.

**Score normalization** — ChromaDB returns distance (lower = more relevant), Pinecone returns similarity (higher = more relevant). Pinecone scores normalized via `1 - score` so both backends share the same `0.7` threshold.

**Conversation memory** — `ConversationBufferWindowMemory` with `k=5` built fresh per request inside `ask()`. Sliding window keeps prompt size bounded. Memory is intentionally in-RAM and per-request — no cross-request persistence.

**Temperature=0.3** — low temperature keeps answers grounded in retrieved context. Higher values risk creative drift from source material.

---

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# fill in GEMINI_API_KEY in .env
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
- Video without captions → Whisper fallback triggered

`POST /chat/ask` edge cases:
- Relevant question → grounded answer, `from_video: true`
- Irrelevant question → LLM fallback, `from_video: false`
- Follow-up question → memory maintained across turns

---

## Limitations

- Conversation memory is in-RAM only — not persistent across server restarts
- No user session isolation — fresh memory per request, no cross-request continuity
- Whisper fallback is slow on CPU (~2-4 min for a 5 min video with `base` model)

---

## Key Learnings

- **RAG Pipeline Design** — full ingestion + retrieval pipeline: transcript extraction → recursive chunking → vector embeddings → similarity retrieval → grounded LLM generation with fallback
- **Advanced RAG** — two-stage relevance filtering (score threshold + LLM-as-a-Judge) and metadata filtering for scoped per-video retrieval
- **Vector Database & Score Normalization** — handled backend-specific score scales (Chroma distance vs Pinecone similarity) with `1 - score` normalization for a unified threshold
- **Pydantic-Settings Config** — `BaseSettings` with `@lru_cache` for validated, type-safe config as a singleton — replaces scattered `os.getenv()` calls
- **Module-Level Singletons** — production FastAPI pattern: expensive resources initialized once in `lifespan()`, accessed directly in services — no DI chain needed
- **Typed Exception Hierarchy** — base exception + domain subclasses + global handlers: routes stay clean, errors always return correct HTTP status codes
- **Dual Transcript Strategy** — yt-dlp primary with FasterWhisper lazy-loaded fallback, safe temp file handling via `pathlib`
- **Conversation Memory** — `ConversationBufferWindowMemory` with sliding window keeps prompt size bounded across long sessions