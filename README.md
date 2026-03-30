# TubeAssist 🎬

> AI-powered YouTube video assistant — ask questions about any YouTube video using a full RAG pipeline.

---

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C?style=flat)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Local-FF6B35?style=flat)
![Pinecone](https://img.shields.io/badge/Pinecone-Production-00B388?style=flat)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=flat&logo=google&logoColor=white)

---

## What is TubeAssist?

TubeAssist lets you paste any YouTube URL and instantly start asking questions about the video — powered by a full RAG pipeline. The system fetches the video transcript via yt-dlp (with FasterWhisper (base) as fallback), chunks it recursively , converts chunks into vector embeddings using Gemini Embeddings, stores them in ChromaDB (locally) or Pinecone (production), and retrieves the most relevant context to answer your questions using Gemini 2.5 Flash.

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
│  TranscriptService → ChunkingService     │
│  (yt-dlp primary,    (RecursiveCharacter │
│   Whisper fallback)   TextSplitter)      │
│                          │               │
│                          ▼               │
│                 EmbeddingService         │
│                 (Gemini Embeddings)      │
│                          │               │
│                          ▼               │
│                 VectorStoreService       │
│                 (ChromaDB / Pinecone)    │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│           RAG QUERY PIPELINE             │
│                                          │
│  User Question → RetrieverService        │
│                  (similarity search      │
│                   + score filtering)     │
│                          │               │
│                  score < 0.7?            │
│                  ├── YES → RAG flow      │
│                  └── NO  → LLM fallback  │
│                          │               │
│                          ▼               │
│                  RAGService              │
│                  (context + prompt       │
│                   + memory)              │
│                          │               │
│                          ▼               │
│                  Gemini 2.5 Flash        │
│                  (answer generation)     │
└──────────────────────────────────────────┘
```

---

## AI Engineering Concepts Implemented

### Retrieval-Augmented Generation (RAG)
Instead of relying on the LLM's training knowledge, TubeAssist retrieves factual context directly from the video transcript before generating a response. This grounds every answer in actual video content and reduces hallucinations.

### Relevance-Score Filtering
Retrieved chunks are filtered by cosine distance score (threshold = 0.7). Chunks scoring above the threshold are considered irrelevant — triggering the LLM fallback instead of passing noisy context to Gemini. This prevents the LLM from generating misleading answers from unrelated chunks.

### Dual Transcript Strategy
yt-dlp is used as the primary caption extractor (fast, no compute). If no captions are available, FasterWhisper transcribes the audio locally as fallback. The Whisper model loads lazily — only when actually needed — keeping RAM usage low on free-tier servers.

### Recursive Character Chunking
The transcript is split into overlapping chunks using `RecursiveCharacterTextSplitter` (`chunk_size=1000`, `chunk_overlap=200`). The overlap ensures semantic continuity at chunk boundaries — retrieved chunks never start mid-thought.

### Vector Embeddings
Each chunk is converted into a high-dimensional vector using Gemini Embeddings (`gemini-embedding-001`, 3072 dimensions). Semantically similar text produces geometrically close vectors — enabling dense retrieval rather than keyword matching.

### Environment-Based Vector Store Switching
`VECTOR_STORE` env var controls which backend initializes at startup — `chroma` for local development, `pinecone` for production. No code changes required between environments. Both backends implement the same interface (`add_documents`, `similarity_search`, `video_exists`).

### Conversation Memory
`ConversationBufferWindowMemory` maintains a sliding window of recent chat history (`k=5` turns) via `MessagesPlaceholder` — enabling follow-up questions while keeping prompt size bounded.

### Duplicate Ingestion Guard
Before processing, the system checks whether a `video_id` already exists in the vector store. If it does, ingestion is skipped — avoiding redundant embedding computation and duplicate vector storage.

### Dependency Injection
All services use constructor-based DI. FastAPI's `Depends()` with `@lru_cache` manages singletons (stateless expensive services like `EmbeddingService`, `VectorStoreService`) and request-scoped instances (stateful services like `MemoryService`, `RAGService`, `IngestionService`).

---

## Tech Stack

### Backend
| Technology | Role |
|---|---|
| FastAPI | REST API framework |
| LangChain | RAG orchestration, memory, prompt templates |
| ChromaDB | Local vector database |
| Pinecone | Cloud vector database (production) |
| Gemini 2.5 Flash | LLM for answer generation |
| Gemini Embeddings | Text → vector conversion (3072 dimensions) |
| yt-dlp | Primary transcript + metadata extraction |
| FasterWhisper | Fallback audio transcription (lazy loaded) |
| Pydantic | Request/response validation |
| Uvicorn | ASGI server |

### Frontend
| Technology | Role |
|---|---|
| React 18 | UI framework |
| Vite | Build tool |
| Axios | HTTP client with interceptors |

---

## Project Structure

```
tubeassist/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── db/
│   │   │   └── chroma/                    # ChromaDB persistent storage
│   │   ├── routes/
│   │   │   ├── ingest_route.py            # POST /videos/ingest
│   │   │   └── chat_route.py              # POST /chat/ask
│   │   ├── services/
│   │   │   ├── providers/
│   │   │   │   ├── metadata_provider.py   # video metadata via yt-dlp
│   │   │   │   ├── whisper_provider.py    # FasterWhisper fallback (lazy loaded)
│   │   │   │   └── youtube_provider.py    # yt-dlp caption extraction
│   │   │   ├── transcript_service.py      # transcript orchestration
│   │   │   ├── chunking_service.py        # RecursiveCharacterTextSplitter
│   │   │   ├── embedding_service.py       # Gemini embeddings
│   │   │   ├── vector_store_service.py    # ChromaDB / Pinecone switching
│   │   │   ├── retriever_service.py       # similarity search + score filtering
│   │   │   ├── memory_service.py          # ConversationBufferWindowMemory
│   │   │   ├── ingestion_service.py       # ingestion orchestrator
│   │   │   └── rag_service.py             # RAG + LLM fallback orchestrator
│   │   ├── dependencies.py                # DI wiring (singletons + request-scoped)
│   │   ├── test/                          # service-level test scripts
│   │   └── main.py                        # FastAPI app + CORS
│   ├── .env.example
│   ├── render.yaml
│   └── requirements.txt
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── VideoInput.jsx             # URL input + validation
    │   │   ├── ChatWindow.jsx             # scrollable message list
    │   │   ├── ChatInput.jsx              # auto-resize textarea
    │   │   ├── MessageBubble.jsx          # user/AI bubble + general knowledge badge
    │   │   └── StatusBar.jsx              # processing/thinking/error/success states
    │   ├── hooks/
    │   │   ├── useVideoIngest.js          # ingestion state + status error handling
    │   │   └── useChat.js                 # chat state + from_video flag
    │   ├── api/
    │   │   ├── client.js                  # axios instance + interceptors
    │   │   └── tubeassist.js              # ingestVideo(), askQuestion()
    │   ├── utils/
    │   │   └── validateYouTubeUrl.js      # URL regex validation
    │   ├── App.jsx
    │   └── index.css
    ├── .env.example
    └── package.json
```

---

## API Reference

### POST `/videos/ingest`

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

### POST `/chat/ask`

**Request**
```json
{
  "question": "What are microplastics?",
  "video_id": "VIDEO_ID"
}
```

**Response**
```json
{
  "answer": "Microplastics are...",
  "sources": [{ "video_id": "...", "chunk_index": 3, "title": "...", "author": "..." }],
  "from_video": true
}
```

`from_video: false` when the answer comes from general LLM knowledge.

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

cp .env.example .env          # add your keys
uvicorn app.main:app --reload
# API running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_URL
npm run dev
# App running at http://localhost:5173
```

---

## Environment Variables

### `backend/.env`
```
GEMINI_API_KEY=your-gemini-api-key

# "chroma" for local, "pinecone" for production
VECTOR_STORE=chroma

# Required only when VECTOR_STORE=pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX=tubeassist
```

### `frontend/.env`
```
VITE_API_URL=http://localhost:8000
```

---

## Deployment

**Frontend** — deployed on Vercel. Set `VITE_API_URL` to the backend's production URL in Vercel's environment variables dashboard.

**Backend** — deployed on Render via `render.yaml`. Uses Pinecone as the vector store in production — set `VECTOR_STORE=pinecone` and secret keys in Render's environment variables dashboard.

**Vector store strategy** — ChromaDB for local development (embedded, zero config, persisted to `db/chroma/`), Pinecone for production (cloud-hosted, persistent across deploys). Switching requires only a single env var change — no code modifications needed.

---

## How It Works — End to End

1. User pastes a YouTube URL → frontend validates format via regex before sending to backend
2. Backend extracts `video_id` from URL, checks if already indexed — skips if duplicate
3. yt-dlp downloads captions. If unavailable, FasterWhisper transcribes audio (lazy loaded)
4. yt-dlp extracts video metadata (`title`, `author`) separately
5. Transcript split into chunks by recursive text splitter (`chunk_size=1000`, `chunk_overlap=200`) with `video_id`, `title`, `author`, `chunk_index` metadata
6. Each chunk embedded via Gemini Embeddings → stored in ChromaDB or Pinecone
7. User asks a question → `video_id` sent with every query
8. Question embedded → cosine similarity search filtered by `video_id` → top-6 chunks retrieved with scores
9. Chunks filtered by cosine distance threshold (0.7) — irrelevant chunks discarded
10. Relevant chunks found → RAG flow: context + chat history + question → Gemini 2.5 Flash → `from_video: true`
11. No relevant chunks → LLM fallback: general knowledge answer → `from_video: false`
12. Frontend displays answer — amber "General knowledge" badge shown when `from_video` is false

---

## Key Design Decisions

**Why relevance-score filtering?** Retrieval always returns k results regardless of actual relevance. Without score filtering, unrelated questions receive irrelevant chunks as context — causing Gemini to produce confusing off-topic answers. Score filtering ensures the LLM fallback fires correctly for truly unrelated questions.

**Why yt-dlp over youtube-transcript-api?** yt-dlp handles caption extraction and metadata in one library, supports more video formats, and is actively maintained. youtube-transcript-api has no metadata support and stricter rate limiting.

**Why lazy Whisper loading?** FasterWhisper base model requires ~600MB RAM. Loading at startup on Render's free tier (512MB) would cause immediate OOM crashes. Lazy loading means Whisper only loads when a video has no captions — most tech and educational videos have auto-generated captions, so Whisper rarely fires in practice.

**Why Pinecone for production?** ChromaDB is embedded — it writes to disk. Render's free tier has ephemeral storage that wipes on every deploy. Pinecone is cloud-hosted and persistent regardless of server restarts or redeployments.