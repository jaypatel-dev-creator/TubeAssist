# TubeAssist — Backend

FastAPI backend implementing a full RAG pipeline over YouTube video transcripts. Accepts a video URL, extracts and indexes the transcript, then answers natural language questions using retrieved context and Gemini 2.5 flash as LLM. 

---

## Tech Stack

| Technology | Purpose |
|---|---|
| FastAPI + Uvicorn | REST API, ASGI server |
| LangChain | RAG orchestration, prompt templates, memory |
| ChromaDB | Local vector store |
| Gemini 2.5 Flash | LLM for answer generation |
| Gemini Embeddings | Text → vector conversion |
| yt-dlp | Primary transcript extraction |
| Whisper | Fallback transcript extraction |
| yt-dlp | Video metadata (title, author) |
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
│   │   │   ├── youtube_provider.py   # youtube-transcript-api
│   │   │   ├── whisper_provider.py   # Whisper fallback
│   │   │   └── metadata_provider.py  # video title, author
│   │   ├── transcript_service.py     # transcript orchestration
│   │   ├── chunking_service.py       # RecursiveCharacterTextSplitter
│   │   ├── embedding_service.py      # Gemini embeddings
│   │   ├── vector_store_service.py   # ChromaDB read/write
│   │   ├── retriever_service.py      # similarity search + metadata filter
│   │   ├── memory_service.py         # ConversationBufferMemory
│   │   ├── ingestion_service.py      # ingestion orchestrator
│   │   └── rag_service.py            # RAG query orchestrator
│   └── main.py                       # FastAPI app + CORS
├── vectorstore/                      # ChromaDB persistence
├── .env
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
    │         ├─► yt-dlp                          # primary
    │         └─► Whisper                         # fallback if unavailable
    │
    ├─► metadata_provider                         # title, author via yt-dlp
    │
    ├─► ChunkingService                           # RecursiveCharacterTextSplitter
    │         chunk_size=1000, chunk_overlap=200
    │         metadata: video_id, title, author
    │
    └─► VectorStoreService → ChromaDB             # embed + persist
```

### Phase 2 — Query

```
User Question
    │
    ├─► RetrieverService.similarity_search()
    │         k=4, filter={"video_id": video_id}  # scoped retrieval
    │
    ├─► MemoryService                              # load chat history
    │
    ├─► ChatPromptTemplate
    │         system + MessagesPlaceholder + context + question
    │
    ├─► Gemini 2.5 Flash (temperature=0.3)
    │
    └─► MemoryService.save_context()              # persist turn
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
  "chunks_stored": 42
}
```

**Response — duplicate**
```json
{
  "status": "already_indexed",
  "video_id": "VIDEO_ID",
  "video_title": "Video Title Here"
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
  "sources": [
    { "video_id": "VIDEO_ID", "chunk_index": 3, "title": "..." }
  ]
}
```

---

## Key Implementation Details

**Dual transcript strategy** — `yt-dlp` is attempted first (fast, no compute). If the video has no captions, `TranscriptService` automatically falls back to Whisper for audio-based transcription.

**Chunking strategy** — `RecursiveCharacterTextSplitter` with `chunk_size=1000`
and `chunk_overlap=200`. The overlap ensures continuity at chunk boundaries —
retrieved chunks avoid abrupt mid-sentence starts. Each chunk carries
`video_id`, `title`, and `author` as metadata.

**Scoped vs global retrieval** — `RetrieverService` supports two modes:
- `video_id` provided → metadata filter applied → answers only from that video
- `video_id` is `None` → global search across all indexed videos (if in future we allow user to search across multiple indexed videos)

**Duplicate ingestion guard** — `VectorStoreService.video_exists()` checks ChromaDB before processing. Prevents redundant embedding computation on re-submission of the same URL.

**Conversation memory** — `ConversationBufferMemory` with `MessagesPlaceholder` maintains full chat history per session. Enables follow-up questions without the user repeating context.

**Temperature=0.3** — kept low to reduce hallucination and keep answers grounded in retrieved context. Higher values would introduce more creativity but risk drifting from the source material.

---

## Setup

```bash
cd backend

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env           # add your GEMINI_API_KEY
```

### Environment Variables

```
GEMINI_API_KEY=your-gemini-api-key-here
```

### Run

```bash
uvicorn app.main:app --reload
# API running at http://localhost:8000
# Docs at http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google Gemini API key for LLM + embeddings |
---

## ⚠️ Limitations

* Conversational memory is stored in RAM (not persistent)
* No user session isolation yet
* Partial ingestion recovery not handled
* Frontend not integrated yet

---

## 🔮 Future Improvements

* Session-based persistant  memory (STM) (Redis)
* Multi-user support
* Streaming responses
* Making use of advanced RAG techniques 
* Evaluation metrics (RAG quality)
* Implementing LLM fallback or  Dual retriever with external knowledge base (Wikipedia / domain sources)
  for answering questions beyond video context 
* Multi video ingestion
---

## Key Learnings

- **RAG Pipeline Design** — built a full ingestion + retrieval pipeline from scratch: transcript extraction → semantic chunking → vector embeddings → ChromaDB storage → similarity retrieval → grounded LLM generation
- **Vector Database & Metadata Filtering** — used ChromaDB with `video_id` metadata tags to implement scoped retrieval, ensuring answers come only from the active video despite multiple videos sharing one collection
- **Semantic Chunking** — applied `RecursiveCharacterTextSplitter` with `chunk_size=1000` and `chunk_overlap=200` to preserve context boundaries across chunk splits
- **Dual Transcript Strategy** — implemented yt-dlp as primary caption extractor with FasterWhisper as automatic fallback for videos without captions, using `pathlib` for sato anfe temp file handling
- **Conversation Memory** — integrated `ConversationBufferMemory` with `MessagesPlaceholder` to maintain full chat history across turns, enabling follow-up questions without context loss
- **LLM Grounding** — used system prompt constraints to anchor Gemini 2.5 Flash strictly to retrieved context, preventing hallucinations and keeping answers traceable to the video
- **FastAPI Service Design** — structured backend into routes, services, and providers with Pydantic validation and CORS middleware for clean separation of concerns
- **Duplicate Ingestion Guard** — implemented `video_exists()` check before processing to skip redundant embedding computation on re-submitted URLs

---

## 🧑‍💻 Author

Jay


