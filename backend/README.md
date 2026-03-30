# TubeAssist — Backend

FastAPI backend implementing a full RAG pipeline over YouTube video transcripts. Accepts a video URL, extracts and indexes the transcript, then answers natural language questions using retrieved context and LLM fallback. 

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
| yt-dlp | Primary caption extraction + video metadata extraction|
| FasterWhisper | Fallback audio transcription (lazy loaded) |
| Pydantic | Request/response validation |

---

## Backend Structure

```
backend/
├── app/
│   ├── core/
│   │   └── config.py                 # env vars
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
│   │   ├── retriever_service.py      # similarity search + score filtering
│   │   ├── memory_service.py         # ConversationBufferWindowMemory
│   │   ├── ingestion_service.py      # ingestion orchestrator
│   │   └── rag_service.py            # RAG + LLM fallback orchestrator
│   ├── dependencies.py               # DI wiring (singletons + request-scoped)
│   └── main.py                       # FastAPI app + CORS
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
    ├─► TranscriptService.extract_video_id()      # regex extraction
    │         │
    │         ├─► yt-dlp                          # primary (captions)
    │         └─► FasterWhisper                   # fallback (audio, lazy loaded)
    │
    ├─► metadata_provider                         # title, author via yt-dlp
    │
    ├─► ChunkingService                           # RecursiveCharacterTextSplitter
    │         chunk_size=1000, chunk_overlap=200
    │         metadata: video_id, title, author, chunk_index
    │
    └─► VectorStoreService                        # embed + persist
              ChromaDB (local) / Pinecone (prod)
```

### Phase 2 — Query

```
User Question
    │
    ├─► RetrieverService.retrieve_with_scores()
    │         k=6, filter={"video_id": video_id}
    │         cosine distance threshold = 0.7
    │
    ├─► score < 0.7?
    │         ├── YES → RAG flow (context + prompt → Gemini)  → from_video: true
    │         └── NO  → LLM fallback (general_prompt → Gemini) → from_video: false
    │
    ├─► MemoryService (langchain ConversationBufferWindowMemory)                             # load chat history (last k=5 turns)
    │
    ├─► ChatPromptTemplate
    │         system + MessagesPlaceholder + context + question
    │
    ├─► Gemini 2.5 Flash (temperature=0.3)
    │
    └─► MemoryService.save()                       # persist turn
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
  "video_author":"Video Author Here", 
  "chunks_stored": 42
}
```

**Response — duplicate**
```json
{
  "status": "already_indexed",
  "video_id": "VIDEO_ID",
  "video_title": "Video Title Here",
  "video_author":"Video Author Here"
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

`from_video: false` when answer comes from general LLM knowledge (irrelevant question).

---

## Key Implementation Details

**Relevance-score filtering** — `retrieve_with_scores()` returns chunks with cosine distance scores. Only chunks scoring below `0.7` are passed as context. Chunks above the threshold trigger the LLM general fallback — preventing Gemini from generating misleading answers from unrelated chunks.

**Dual transcript strategy** — yt-dlp attempted first (fast, no compute). Empty or missing captions raise an exception, triggering FasterWhisper fallback. Whisper model loads lazily — only when needed — keeping RAM low on free-tier deployment.

**Chunking strategy** — `RecursiveCharacterTextSplitter` with `chunk_size=1000` and `chunk_overlap=200`. Each chunk carries `video_id`, `title`, `author`, `chunk_index` metadata.

**Scoped vs global retrieval** — `video_id` provided → metadata filter applied (scoped). `video_id` is `None` → global search across all indexed videos. As per current implementation,  Frontend always sends `video_id` — global path exists for API-level flexibility.

**Duplicate ingestion guard** — `video_exists()` checks the vector store before processing. Prevents redundant embedding computation on re-submitted URLs.

**Dependency Injection** — constructor-based DI across all services. `dependencies.py` wires the full graph using `@lru_cache` for singletons (`EmbeddingService`, `VectorStoreService`, `RetrieverService`) and plain functions for request-scoped instances (`MemoryService`, `RAGService` ,`IngestionService`).

**Conversation memory** — `ConversationBufferWindowMemory` with `k=5` maintains a sliding window of recent turns via `MessagesPlaceholder`. Keeps prompt size bounded on long conversations.

**Temperature=0.3** — low temperature keeps answers grounded in retrieved context. Higher values risk creative drift from source material.

---

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for LLM + embeddings |
| `VECTOR_STORE` | No | `chroma` (default) or `pinecone` |
| `PINECONE_API_KEY` | Pinecone only | Pinecone API key |
| `PINECONE_INDEX` | Pinecone only | Index name (default: `tubeassist`) |

---

## Limitations

- Conversation memory is in-RAM only — not persistent across server restarts
- No user session isolation — single shared memory instance per server process
- Whisper fallback is slow on CPU (~2-4 min for a 5 min video with `base` model)

---

## Future Improvements

- Session-based persistent memory
- Multi-user support with isolated memory per session
- Streaming responses
- Advanced RAG techniques (HyDE, re-ranking, MMR)
- RAG evaluation metrics (faithfulness, relevance, context recall, context accuracy)


---

## Key Learnings

- **RAG Pipeline Design** — built a full ingestion + retrieval pipeline: transcript extraction → Recursive Character based chunking → vector embeddings → vector store → similarity retrieval → grounded LLM generation along with LLM fallback. 
- **Relevance-Score Filtering** — used cosine distance thresholding to distinguish relevant from irrelevant chunks, enabling clean LLM fallback for out-of-context questions
- **Vector Database & Metadata Filtering** — scoped retrieval using `video_id` metadata tags ensures answers come only from the active video despite multiple videos sharing one collection
- **Environment-Based Vector Store Switching** — single `VECTOR_STORE` env var switches between ChromaDB (local) and Pinecone (production) without code changes
- **Dual Transcript Strategy** — yt-dlp primary with FasterWhisper lazy-loaded fallback, using `pathlib` for safe temp file handling
- **Dependency Injection** — constructor-based DI with FastAPI `Depends()` and `@lru_cache` for singleton vs request-scoped lifecycle management
- **Conversation Memory** — `ConversationBufferWindowMemory` with sliding window keeps prompt size bounded across long sessions
- **FastAPI Service Design** — structured into routes, services, providers, and dependencies with clean separation of concerns

---

