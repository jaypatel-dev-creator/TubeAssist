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
│   ├── useVideoIngest.js    # ingestion state, video_id, video_title, error handling
│   └── useChat.js           # message history, from_video flag
├── api/
│   ├── client.js            # plain axios instance (baseURL, timeout, Content-Type)
│   └── tubeassist.js        # ingestVideo(), askQuestion()
├── utils/
│   └── validateYouTubeUrl.js
├── App.jsx                  # layout + state orchestration
└── index.css
```

---

## API Integration

All requests route through a single plain axios instance in `client.js`:

```js
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 180000,  // 3 min — accounts for Whisper fallback transcription
  headers: { "Content-Type": "application/json" }
});
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

**Manual response unwrap** — `response.data` extracted manually in each hook after axios call. 

**Manual error extraction** — catch blocks in both `useVideoIngest` and `useChat` extract error messages via `err.response?.data?.detail` → `err.response?.data?.message` → `err.message` fallback chain.


**`from_video` flag** — `useChat` reads `data.from_video` from each response and stores it on the message object. `MessageBubble` renders an amber "General knowledge — not from video" badge when `fromVideo === false`.

**Guard condition** — `ChatInput` disabled until `isVideoReady = !!videoTitle && !isIngesting`.

**Already indexed** — `status: "already_indexed"` handled as success path with distinct status message.

**Chat reset** — `useEffect` watches `isIngesting` and calls `resetChat()` on new video load.