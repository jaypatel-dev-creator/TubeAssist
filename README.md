# TubeAssist 🎬

> AI-powered YouTube video assistant — ask questions about any youtube video using RAG pipeline.
---

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135+-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C?style=flat)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-FF6B35?style=flat)
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=flat&logo=google&logoColor=white)

---

## What is TubeAssist?

TubeAssist lets you paste any YouTube URL and instantly start asking questions about the video — powered by a full RAG pipeline. The system fetches the video transcript, chunks it , converts chunks into vector embeddings using gemini-embedding-001 , stores them in ChromaDB, and retrieves the most relevant context to answer your questions using  gemini-2.5-flash


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
│  (fetch + parse)     (Recursive          │
│                       CharacterText      │
│                       Splitter)          │
│                          │               │
│                          ▼               │
│                 EmbeddingService         │
│                 (Gemini Embeddings)      │
│                          │               │
│                          ▼               │
│                 VectorStoreService       │
│                 (ChromaDB storage)       │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│           RAG QUERY PIPELINE             │
│                                          │
│  User Question → RetrieverService        │
│                  (similarity search)     │
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
Instead of relying on the LLM's training knowledge, TubeAssist retrieves factual context directly from the video transcript before generating a response. This eliminates hallucinations and grounds every answer in the actual video content.

### Recursive Character Chunking
The transcript is split into overlapping chunks using separator-based splitting
(`\n\n`, `\n`, spaces). This preserves sentence boundaries where possible,
avoiding mid-sentence cuts — but splits are based on character count,
not meaning or context.

### Vector Embeddings
Each chunk is converted into a high-dimensional vector using Gemini Embeddings. Semantically similar text produces vectors that are geometrically close — enabling similarity-based retrieval (dense retrieval) rather than keyword matching.

### Vector Store (ChromaDB)
Embeddings are persisted in ChromaDB, a local vector database. At query time, the user's question is also embedded and compared against stored vectors using cosine similarity to find the most relevant chunks.

### Conversation Memory
LangChain's `ConversationBufferWindowMemory` maintains a sliding window of
recent chat history across turns via `MessagesPlaceholder` in the prompt
template — enabling follow-up questions while keeping context bounded to
the last `k` exchanges, preventing prompt bloat on long conversations.

### Duplicate Ingestion Guard
Before processing, the system checks whether a `video_id` already exists in ChromaDB. If it does, ingestion is skipped — avoiding redundant embedding computation and duplicate vector storage.

### Metadata Filtering
Each chunk is stored with a `video_id` metadata field. At retrieval time,
ChromaDB filters by this field — ensuring only chunks belonging to the
queried video are searched, preventing cross-video context leakage.

---

## Tech Stack

### Backend
| Technology | Role |
|---|---|
| FastAPI | REST API framework |
| LangChain | RAG orchestration, memory, prompt templates |
| ChromaDB | Local vector database |
| Gemini 2.5 Flash | LLM for answer generation |
| Gemini Embeddings | Text → vector conversion |
| yt-dlp | YouTube transcript extraction (with Whisper fallback) |
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
│   │   │   └── config.py              # env vars via pydantic-settings
│   │   ├── db/
│   │   │   └── chroma/                # ChromaDB persistent storage
│   │   ├── routes/
│   │   │   ├── ingest_route.py        # POST /videos/ingest
│   │   │   └── chat_route.py          # POST /chat/ask
│   │   ├── services/
│   │   │   ├── providers/
│   │   │   │   ├── metadata_provider.py   # video metadata extraction
│   │   │   │   ├── whisper_provider.py    # Whisper fallback transcription
│   │   │   │   └── youtube_provider.py    # yt-dlp transcript extraction
│   │   │   ├── transcript_service.py      # fetch YouTube transcript
│   │   │   ├── chunking_service.py        # recursive character chunking
│   │   │   ├── embedding_service.py       # Gemini embeddings
│   │   │   ├── vector_store_service.py    # ChromaDB operations
│   │   │   ├── retriever_service.py       # similarity search
│   │   │   ├── memory_service.py          # conversation memory
│   │   │   ├── ingestion_service.py       # ingestion orchestrator
│   │   │   └── rag_service.py             # RAG query orchestrator
│   │   ├── test/
│   │   │   ├── test_chunking.py           # chunking tests
│   │   │   ├── test_duplicate_ingestion.py# duplicate guard tests
│   │   │   ├── test_embedding.py          # embedding tests
│   │   │   ├── test_memory.py             # memory tests
│   │   │   ├── test_retriever.py          # retriever tests
│   │   │   ├── test_transcript.py         # transcript tests
│   │   │   ├── test_vector_store.py       # vector store tests
│   │   │   └── testing_approac.txt        # testing notes
│   │   └── main.py                        # FastAPI app + CORS
│   ├── .env
│   ├── requirements.txt
│   
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── VideoInput.jsx         # URL input + validation
    │   │   ├── ChatWindow.jsx         # scrollable message list
    │   │   ├── ChatInput.jsx          # auto-resize textarea
    │   │   ├── MessageBubble.jsx      # user/AI bubble + thinking indicator
    │   │   └── StatusBar.jsx          # processing/thinking/error/success states
    │   ├── hooks/
    │   │   ├── useVideoIngest.js      # ingestion state + handler
    │   │   └── useChat.js             # chat state + handler
    │   ├── api/
    │   │   ├── client.js              # axios instance + interceptors
    │   │   └── tubeassist.js          # ingestVideo(), askQuestion()
    │   ├── utils/
    │   │   └── validateYouTubeUrl.js  # URL regex validation
    │   ├── App.jsx
    │   └── index.css
    ├── .env
    └── package.json
```

---

## API Reference

### POST `/videos/ingest`
Fetches transcript, chunks, embeds, and stores in ChromaDB.

**Request**
```json
{ "url": "https://www.youtube.com/watch?v=VIDEO_ID" }
```

**Response**
```json
{
  "status": "success",
  "video_id": "VIDEO_ID",
  "video_title": "Respective title of the video",
  "chunks_stored": 42
}
```
Returns `"status": "already_indexed"` if the video was previously ingested — skips reprocessing.

---

### POST `/chat/ask`
Retrieves relevant chunks and generates a grounded answer.

**Request**
```json
{
  "question": "Question asked by the user",
  "video_id": "VIDEO_ID"
}
```

**Response**
```json
{
  "answer": "Response from the LLM...",
  "sources": [{ "video_id": "...", "chunk_index": 3 }]
}
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Gemini API key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# create .env
cp .env.example .env
# add your GEMINI_API_KEY to .env

python run.py
# API running at http://localhost:8000
```

### Frontend Setup
```bash
cd frontend
npm install

# create .env
cp .env.example .env
# VITE_API_URL=http://localhost:8000

npm run dev
# App running at http://localhost:5173
```

---

## Environment Variables

### `backend/.env`
```
GEMINI_API_KEY=your-gemini-api-key
```

### `frontend/.env`
```
VITE_API_URL=http://localhost:8000
```

---

## How It Works — End to End

1. User pastes a YouTube URL and clicks **Load**
2. Frontend validates the URL (regex check) before sending to backend
3. Backend extracts the `video_id` from the URL via regex
4. yt-dlp attempts to download captions — if no captions found, FasterWhisper transcribes the audio as fallback
5. yt-dlp extracts video metadata (`title`, `author`) separately
6. Transcript is split into chunks via `ChunkingService` (RecursiveCharacterTextSplitter — chunk_size=1000, chunk_overlap=200)
7. Each chunk is tagged with `video_id`, `title`, `author` as metadata
8. Each chunk is converted to a vector embedding using Gemini Embeddings
9. Embeddings are stored in ChromaDB — if `video_id` already exists, ingestion is skipped
10. User asks a question in the chat — `video_id` is sent alongside every query
11. Question is embedded and compared against stored vectors filtered by `video_id` (cosine similarity)
12. Top-k=4 most relevant chunks are retrieved
13. Retrieved chunks + conversation history + question are passed to Gemini 2.5 Flash
14. LLM generates a grounded answer based only on retrieved context — if no relevant chunks found, responds with "I couldn't find relevant information in the indexed content"
15. Answer is returned to frontend and displayed as a chat bubble

---
