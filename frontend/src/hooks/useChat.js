import { useState, useCallback } from "react";
import { askQuestion } from "../api/tubeassist";

// ─── Helper ───────────────────────────────────────────────────────────────────
function makeMessage(role, text, isError = false) {
  return {
    id: crypto.randomUUID(),
    role,
    text,
    timestamp: Date.now(),
    isError,
  };
}

// ─── Hook ─────────────────────────────────────────────────────────────────────
/**
 * useChat
 *
 * Handles everything related to the chat — sending messages,
 * managing history, and resetting on new video.
 *
 * Params:
 *   videoId      — video_id from useVideoIngest (sent to backend with each question)
 *   isVideoReady — guard: chat is disabled until this is true
 *
 * Returns:
 *   messages     — array of { id, role, text, timestamp, isError }
 *   isThinking   — true while waiting for AI response
 *   chatStatus   — "thinking" | "error" | null
 *   chatMsg      — message string for StatusBar
 *   handleSend   — call this with a question string
 *   resetChat    — clears message history (called on new video load)
 */
export default function useChat(videoId, isVideoReady) {
  const [messages,   setMessages]   = useState([]);
  const [isThinking, setIsThinking] = useState(false);
  const [chatStatus, setChatStatus] = useState(null);
  const [chatMsg,    setChatMsg]    = useState("");

  const resetChat = useCallback(() => {
    setMessages([]);
    setChatStatus(null);
    setChatMsg("");
  }, []);

  const handleSend = useCallback(async (question) => {
    // Guard: do nothing if video isn't ready or already waiting
    if (!isVideoReady || isThinking) return;

    // Append user message immediately (optimistic update)
    setMessages((prev) => [...prev, makeMessage("user", question)]);
    setIsThinking(true);
    setChatStatus("thinking");
    setChatMsg("Thinking…");

    try {
      const data = await askQuestion(question, videoId);           // ← videoId
      setMessages((prev) => [...prev, makeMessage("ai", data.answer)]);
      setChatStatus(null);
      setChatMsg("");
    } catch (err) {
      const errMsg = err.message || "Something went wrong.";
      setMessages((prev) => [...prev, makeMessage("ai", errMsg, true)]);
      setChatStatus("error");
      setChatMsg(errMsg);
    } finally {
      setIsThinking(false);
    }
  }, [isVideoReady, isThinking, videoId]);

  return {
    messages,
    isThinking,
    chatStatus,
    chatMsg,
    handleSend,
    resetChat,
  };
}