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
│   ├── MessageBubble.jsx    # user/AI bubbles + general knowledge badge
│   └── StatusBar.jsx        # processing / thinking / error / success states
├── hooks/
│   ├── useVideoIngest.js    # ingestion state, video_id, video_title, status error handling
│   └── useChat.js           # message history, from_video flag
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
POST /videos/ingest  → { url }               → { status, video_id, video_title }
POST /chat/ask       → { question, video_id } → { answer, sources, from_video }
```

---

## Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

---

## Key Implementation Notes

**Status error handling** — backend returns `{ status: "error", message: "..." }` as HTTP 200 for handled failures. `useVideoIngest` explicitly checks `data.status === "error"` — preventing "Untitled Video" from appearing on failed ingestion.

**`from_video` flag** — `useChat` reads `data.from_video` from each response and stores it on the message object. `MessageBubble` renders an amber "General knowledge — not from video" badge when `fromVideo === false`.

**Guard condition** — `ChatInput` disabled until `isVideoReady = !!videoTitle && !isIngesting`.

**Already indexed** — `status: "already_indexed"` handled as success path with distinct status message.

**Optimistic updates** — user messages appended immediately before API call resolves.

**Chat reset** — `useEffect` watches `isIngesting` and calls `resetChat()` on new video load.