# TubeAssist — Frontend

React-based chat interface for the TubeAssist RAG pipeline. Handles video ingestion, real-time chat state, and API communication with the FastAPI backend.

---



## Project Structure

```
src/
├── components/
│   ├── VideoInput.jsx       # URL field, validation, load state
│   ├── ChatWindow.jsx       # scrollable message list, auto-scroll
│   ├── ChatInput.jsx        # auto-resize textarea, Enter to send
│   ├── MessageBubble.jsx    # user/AI bubbles + thinking indicator
│   └── StatusBar.jsx        # processing / thinking / error / success states
├── hooks/
│   ├── useVideoIngest.js    # ingestion state, video_id, video_title
│   └── useChat.js           # message history
├── api/
│   ├── client.js            # axios base instance + interceptors
│   └── tubeassist.js        # ingestVideo(), askQuestion()
├── utils/
│   └── validateYouTubeUrl.js
├── App.jsx                  # layout + state orchestration
└── index.css                
```

---

## API Integration

All requests route through a single axios instance in `client.js`:

```js
// Response interceptor — unwraps data, normalizes FastAPI errors
client.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(new Error(error.response?.data?.detail || error.message))
);
```

Two endpoints consumed:

```js
POST /videos/ingest   → { url }                        → { video_id, video_title, status }
POST /chat/ask        → { question, video_id }          → { answer, sources }
```

---



## Setup

```bash
cd frontend
npm install

cp .env.example .env
# set VITE_API_URL=http://localhost:8000

npm run dev
```


## Key Implementation Notes

**Guard condition** — `ChatInput` is fully disabled until a video is successfully ingested.

**Already indexed** — backend returns `status: "already_indexed"` for duplicate videos. Frontend handles this as a success path with a distinct status message — no re-ingestion triggered.

