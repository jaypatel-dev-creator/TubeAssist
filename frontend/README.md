# TubeAssist — Frontend

React-based chat interface for the TubeAssist RAG pipeline. Handles video ingestion, session management, real-time chat state, and API communication with the FastAPI backend.

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
│   ├── useVideoIngest.js    # ingestion state, video_id, session_id generation, error handling
│   └── useChat.js           # message history, session_id forwarding, from_video flag
├── api/
│   ├── client.js            # plain axios instance (baseURL, timeout, Content-Type)
│   └── tubeassist.js        # ingestVideo(), askQuestion(question, videoId, sessionId)
├── utils/
│   └── validateYouTubeUrl.js
├── App.jsx                  # layout + state orchestration + session_id wiring
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
POST /videos/ingest  → { url }
                     ← { status, video_id, video_title, video_author, chunks_stored }

POST /chat/ask       → { question, video_id, session_id }
                     ← { answer, sources, from_video }
```

---

## Session Management

Each video load generates a `session_id` via `crypto.randomUUID()` inside `useVideoIngest`. This ID is:

- Generated on every successful ingest response (200)
- Generated on 409 (already indexed) — fresh session even for existing videos
- Cleared on ingest error — no session assigned until a video is successfully ready
- Passed from `useVideoIngest` → `App.jsx` → `useChat` as a prop
- Sent with every `POST /chat/ask` request so the backend can maintain per-session conversation history
- Included in `useChat`'s `useCallback` dependency array — `handleSend` always closes over the current session, never a stale one

New video load = new `session_id` = clean isolated history on the backend. No cross-video memory bleed.

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

**Session ID flow** — `useVideoIngest` owns session generation. `App.jsx` destructures `sessionId` alongside `videoId` and passes both into `useChat(videoId, sessionId, isVideoReady)`. `useChat` forwards `sessionId` to every `askQuestion()` call.

**Manual response unwrap** — `response.data` extracted manually in each hook after axios call.

**Manual error extraction** — catch blocks in both `useVideoIngest` and `useChat` extract error messages via `err.response?.data?.error` → `err.response?.data?.detail` → `err.message` fallback chain.

**Markdown rendering** — AI message text renders through `react-markdown`. User messages and error messages render as plain text.

**`from_video` flag** — `useChat` reads `data.from_video` from each response and stores it on the message object. `MessageBubble` renders an amber "General knowledge — not from video" badge when `fromVideo === false`.

**Guard condition** — `ChatInput` disabled until `isVideoReady = !!videoTitle && !isIngesting`.

**Already indexed** — `409` response handled as a success-like state in `useVideoIngest` catch block — extracts `video_id` and `video_title` from the error response body, generates a fresh `session_id`, and unlocks chat with the existing video.

**Chat reset** — `useEffect` watches `isIngesting` and calls `resetChat()` on new video load — clears message history in sync with the new session on the backend.