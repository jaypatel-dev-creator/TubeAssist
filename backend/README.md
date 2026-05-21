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
| Pydantic | Request/response validation |

---

## Backend Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py                 # environment-based config (dev/prod switching)
│   ├── routes/
│   │   ├── ingest_route.py           # POST /videos/ingest
│   │   └── chat_route.py             # POST /chat/ask
│   ├── services/
│   │   ├── providers/
│   │   │   ├── youtube_provider.py   # yt-dlp caption extraction
│   │   │   ├── whisper_provider.py   # FasterWhisper fallback (lazy loaded)
│   │   │   └── metadata_provider.py  # video title, author via yt-dlp
│   │   ├── transcript_service.py     # transcript orchestration
│   │   ├── chunking_service.py       # RecursiveCharacterTextSplitter
│   │   ├── embedding_service.py      # Gemini embeddings
│   │   ├── vector_store_service.py   # ChromaDB / Pinecone switching
│   │   ├── retriever_service.py      # similarity search + score normalization
│   │   ├── memory_service.py         # ConversationBufferWindowMemory
│   │   ├── ingestion_service.py      # ingestion orchestrator
│   │   └── rag_service.py            # RAG + LLM fallback orchestrator
│   ├── dependencies.py               # DI wiring (singletons + request-scoped)
│   └── main.py                       # FastAPI app + environment-based CORS
├── .env.example
├── .env.production                   # local production simulation only (gitignored)
├── render.yaml
└── requirements.txt
```

---

## RAG Pipeline

### Phase 1 — Ingestion

```
YouTube URL
    │
    ├─► TranscriptService.extract_video_id()      # regex extraction
    │         │
    │         ├─► yt-dlp                          # primary transcript extraction
    │         └─► FasterWhisper                   # fallback transcript extraction
    │
    ├─► metadata_provider                         # title, author via yt-dlp
    │
    ├─► VectorStoreService.video_exists()         # duplicate ingestion guard
    │
    ├─► ChunkingService                           # RecursiveCharacterTextSplitter
    │         chunk_size=1000, chunk_overlap=200
    │         metadata: video_id, title, author, chunk_index
    │
    └─► VectorStoreService.add_documents()        # embed + persist
              ChromaDB (local) / Pinecone (prod)
```

### Phase 2 — Query

```
User Question
    │
    ├─► MemoryService.get_history()               # load chat history (last k=5 turns)
    │
    ├─► RetrieverService.retrieve_with_scores()
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
    └─► MemoryService.save()                      # persist turn
```


---

## API Reference

### `POST /videos/ingest`

**Request**
```json
{ "url": "https://www.youtube.com/watch?v=VIDEO_ID" }
```

**Response — first time**
```json
{
  "status": "success",
  "video_id": "VIDEO_ID",
  "video_title": "Video Title Here",
  "video_author": "Video Author Here",
  "chunks_stored": 42
}
```

**Response — duplicate**
```json
{
  "status": "already_indexed",
  "video_id": "VIDEO_ID",
  "video_title": "Video Title Here",
  "video_author": "Video Author Here"
}
```

**Response — error**
```json
{
  "status": "error",
  "message": "Could not fetch transcript. Check if the video exists and is public."
}
```

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

`from_video: false` when answer comes from general LLM knowledge (no relevant context found in video).

---

## Key Implementation Details

**Two-stage relevance filtering** — Stage 1 applies cosine distance threshold (0.7) to filter out mathematically irrelevant chunks. Stage 2 uses LLM-as-a-Judge — the model is instructed to return `"NO_RELEVANT_CONTEXT"` if the retrieved chunks don't actually answer the question. Both stages trigger LLM fallback independently, preventing hallucination from unrelated chunks.

**Dual transcript strategy** — yt-dlp attempted first (fast, no compute). Empty or missing captions raise an exception, triggering FasterWhisper fallback. Whisper model loads lazily — only when needed — keeping RAM low on free-tier deployment.

**Chunking strategy** — `RecursiveCharacterTextSplitter` with `chunk_size=1000` and `chunk_overlap=200`. Splits on natural boundaries (paragraphs → sentences → words). Each chunk carries `video_id`, `title`, `author`, `chunk_index` metadata.

**Score normalization** — ChromaDB returns distance (lower = more relevant), Pinecone returns similarity (higher = more relevant). Pinecone scores are normalized via `1 - score` so both backends share the same `0.7` threshold in `RAGService`.

**Scoped vs global retrieval** — `video_id` provided → metadata filter applied (scoped). `video_id` is `None` → global search across all indexed videos. Frontend always sends `video_id` — global path exists for API-level flexibility.

**Duplicate ingestion guard** — `video_exists()` checks the vector store before processing. Prevents redundant embedding computation on re-submitted URLs. 

**Dependency Injection** — constructor-based DI across all services. `dependencies.py` wires the full graph using `@lru_cache` for singletons (`EmbeddingService`, `VectorStoreService`, `RetrieverService`) and plain functions for request-scoped instances (`MemoryService`, `RAGService`, `IngestionService`).

**Conversation memory** — `ConversationBufferWindowMemory` with `k=5` maintains a sliding window of recent turns via `MessagesPlaceholder`. Keeps prompt size bounded on long conversations.

**Environment-based configuration** — `config.py` reads `APP_ENV` before loading any `.env` file. `APP_ENV=development` (default) loads `.env` with Chroma. `APP_ENV=production` loads `.env.production` for local simulation or reads from Render dashboard in actual deployment. Single `VECTOR_STORE` env var switches between ChromaDB and Pinecone without any code changes.

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

### Simulate production locally

```bash
cp .env.example .env.production
# fill in all production values (Pinecone keys etc.)
APP_ENV=production uvicorn app.main:app --reload
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `APP_ENV` | No | `development` | `development` or `production` |
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key for LLM + embeddings |
| `VECTOR_STORE` | No | `chroma` | `chroma` (local) or `pinecone` (production) |
| `PINECONE_API_KEY` | Pinecone only | — | Pinecone API key |
| `PINECONE_INDEX` | Pinecone only | `tubeassist` | Pinecone index name |

---

## Testing

**Integration testing via Swagger UI** (`http://localhost:8000/docs`):

`POST /videos/ingest` edge cases tested:
- Valid URL → successful ingestion
- Same URL twice → `already_indexed` returned
- Fake URL → error returned
- Video without captions → Whisper fallback triggered

`POST /chat/ask` edge cases tested:
- Relevant question → grounded answer, `from_video: true`
- Irrelevant question → LLM fallback, `from_video: false`
- Follow-up question → memory maintained across turns



---

## Limitations

- Conversation memory is in-RAM only — not persistent across server restarts
- No user session isolation — single shared memory instance per server process
- Whisper fallback is slow on CPU (~2-4 min for a 5 min video with `base` model)

---

## Key Learnings

- **RAG Pipeline Design** — built a full ingestion + retrieval pipeline: transcript extraction → recursive character chunking → vector embeddings → vector store → similarity retrieval → grounded LLM generation with LLM fallback
- **Advanced RAG** — two-stage relevance filtering (score threshold + LLM-as-a-Judge) and metadata filtering for scoped per-video retrieval
- **Vector Database & Score Normalization** — handled backend-specific score scales (Chroma distance vs Pinecone similarity) with `1 - score` normalization for a unified threshold
- **Environment-Based Configuration** — 12-Factor App config pattern: `APP_ENV` drives `.env` file selection, single codebase runs across dev and prod without code changes
- **Dual Transcript Strategy** — yt-dlp primary with FasterWhisper lazy-loaded fallback, safe temp file handling via `pathlib`
- **Dependency Injection** — constructor-based DI with FastAPI `Depends()` and `@lru_cache` for singleton vs request-scoped lifecycle management
- **Conversation Memory** — `ConversationBufferWindowMemory` with sliding window keeps prompt size bounded across long sessions
- **FastAPI Service Design** — structured into routes, services, providers, and dependencies with clean separation of concerns