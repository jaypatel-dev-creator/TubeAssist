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

TubeAssist lets you paste any YouTube URL and instantly start asking questions about the video — powered by a full RAG pipeline. The system fetches the video transcript via yt-dlp (with FasterWhisper as fallback), chunks it recursively, converts chunks into vector embeddings using Gemini Embeddings, stores them in ChromaDB (locally) or Pinecone (production), and retrieves the most relevant context to answer your questions using Gemini 2.5 Flash.

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
│                  (similarity search,     │
│                   video_id filter)       │
│                          │               │
│              Stage 1 — Score filter      │
│              Stage 2 — LLM-as-a-Judge   │
│                  ├── relevant → RAG      │
│                  └── irrelevant → LLM   │
│                          fallback        │
│                          │               │
│                          ▼               │
│                  RAGService              │
│                  (context + memory       │
│                   + Gemini 2.5 Flash)    │
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
| LangChain | RAG orchestration, memory, prompt templates |
| ChromaDB | Local vector database |
| Pinecone | Cloud vector database (production) |
| Gemini 2.5 Flash | LLM for answer generation |
| Gemini Embeddings | Text → vector conversion (3072 dimensions) |
| yt-dlp | Primary transcript + metadata extraction |
| FasterWhisper (base) | Fallback audio transcription (lazy loaded) |
| Pydantic | Request/response validation |

### Frontend
| Technology | Role |
|---|---|
| React 18 + Vite | UI framework + build tool |
| Axios | HTTP client |

---

## Project Structure

```
tubeassist/
├── backend/
│   ├── app/
│   │   ├── core/
│   │   │   └── config.py                  # environment-based config (dev/prod switching)
│   │   ├── db/
│   │   │   └── chroma/                    # ChromaDB persistent storage
│   │   ├── routes/
│   │   │   ├── ingest_route.py            # POST /videos/ingest
│   │   │   └── chat_route.py              # POST /chat/ask
│   │   ├── services/
│   │   │   ├── providers/
│   │   │   │   ├── youtube_provider.py    # yt-dlp caption extraction
│   │   │   │   ├── whisper_provider.py    # FasterWhisper fallback (lazy loaded)
│   │   │   │   └── metadata_provider.py   # video title, author via yt-dlp
│   │   │   ├── transcript_service.py      # transcript orchestration
│   │   │   ├── chunking_service.py        # RecursiveCharacterTextSplitter
│   │   │   ├── embedding_service.py       # Gemini embeddings
│   │   │   ├── vector_store_service.py    # ChromaDB / Pinecone switching
│   │   │   ├── retriever_service.py       # similarity search + score normalization
│   │   │   ├── memory_service.py          # ConversationBufferWindowMemory
│   │   │   ├── ingestion_service.py       # ingestion orchestrator
│   │   │   └── rag_service.py             # RAG + LLM fallback orchestrator
│   │   ├── dependencies.py                # DI wiring (singletons + request-scoped)
│   │   └── main.py                        # FastAPI app + environment-based CORS
│   ├── .env.example
│   ├── .env.production                    # local production simulation only (gitignored)
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
    │   │   ├── useVideoIngest.js          # ingestion state + error handling
    │   │   └── useChat.js                 # chat state + from_video flag
    │   ├── api/
    │   │   ├── client.js                  # plain axios instance (baseURL, timeout)
    │   │   └── tubeassist.js              # ingestVideo(), askQuestion()
    │   ├── utils/
    │   │   └── validateYouTubeUrl.js      # URL regex validation
    │   ├── App.jsx
    │   └── index.css
    ├── .env.example
    └── package.json
```

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
| `APP_ENV` | No | `development` | controls which `.env` file loads — local use only |
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `VECTOR_STORE` | No | `chroma` | `chroma` locally, `pinecone` in production |
| `PINECONE_API_KEY` | Pinecone only | — | Pinecone API key |
| `PINECONE_INDEX` | Pinecone only | `tubeassist` | Pinecone index name |

### `frontend/.env` (local only — never committed)

| Variable | Required | Default | Description |
|---|---|---|---|
| `VITE_API_URL` | No| `http://localhost:8000` | FastAPI backend URL |

---

## Environment-Based Configuration

Three scenarios, same codebase, zero code changes:

**Local dev** — just run normally, no setup needed:
```bash
uvicorn app.main:app --reload
# APP_ENV defaults to "development" → loads .env → uses ChromaDB
```

**Simulate production locally** — prefix with `APP_ENV=production`:
```bash
APP_ENV=production uvicorn app.main:app --reload
# loads .env.production → uses Pinecone
```

**Actual production (Render)** — set all vars directly in Render dashboard:
```
APP_ENV=production
GEMINI_API_KEY=your_key
VECTOR_STORE=pinecone
PINECONE_API_KEY=your_key
PINECONE_INDEX=tubeassist
```

No `.env` files on Render — Render injects vars directly. `load_dotenv` runs but does nothing.

---

## Deployment

**Backend → Render**
Push to GitHub → Render auto-deploys via `render.yaml`. Set `GEMINI_API_KEY` and `PINECONE_API_KEY` manually in Render dashboard (secrets). Everything else is handled by `render.yaml`.

**Frontend → Vercel**
Connect GitHub repo to Vercel. Set `VITE_API_URL=https://your-render-url.com` in Vercel dashboard → Environment Variables. Vite bakes it into the bundle at deploy time.





## Key Design Decisions

**Why two-stage filtering over one?** Score filter alone can't detect semantic irrelevance — a chunk can be mathematically close but contextually wrong. LLM judge alone without pre-filtering wastes tokens on garbage chunks. Together: Stage 1 narrows candidates cheaply, Stage 2 makes the final semantic call.

**Why lazy Whisper loading?** FasterWhisper base model requires ~600MB RAM. Loading at startup on Render's free tier (512MB) causes OOM crashes. Lazy loading means it only loads when a video has no captions — most tech and educational videos have auto-generated captions, so Whisper rarely fires in practice.

**Why Pinecone for production?** ChromaDB is embedded and writes to disk. Render's free tier has ephemeral storage that wipes on every deploy. Pinecone is cloud-hosted and persistent across restarts and redeployments.

**Why yt-dlp over youtube-transcript-api?** yt-dlp handles both caption extraction and metadata in one library, supports more video formats, and is actively maintained.

---

## Limitations

- Conversation memory is in-RAM only — not persistent across server restarts
- No user session isolation — single shared memory instance per server process
- Whisper fallback is slow on CPU (~2-4 min for a 5 min video)

---

## Future Improvements

- Session-based persistent memory (Redis)
- Multi-user support with isolated memory per session
- Streaming responses
- Advanced RAG techniques (HyDE, re-ranking, MMR)
- RAG evaluation metrics (faithfulness, relevance, context recall)