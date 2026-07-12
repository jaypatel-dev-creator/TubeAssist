import { useState, useCallback } from "react";
import { askQuestion } from "../api/tubeassist";

function makeMessage(role, text, isError = false, fromVideo = true) {
  return {
    id: crypto.randomUUID(),
    role,
    text,
    timestamp: Date.now(),
    isError,
    fromVideo,
  };
}

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
    if (!isVideoReady || isThinking) return;

    setMessages((prev) => [...prev, makeMessage("user", question)]);
    setIsThinking(true);
    setChatStatus("thinking");
    setChatMsg("Thinking…");

    try {
      const response = await askQuestion(question, videoId);
      const data = response.data;
      setMessages((prev) => [
        ...prev,
        makeMessage("ai", data.answer, false, data.from_video ?? true),
      ]);
      setChatStatus(null);
      setChatMsg("");
    } catch (err) {
      const message = err.response?.data?.error ||
                      err.response?.data?.detail ||
                      err.message ||
                      "Something went wrong.";
      setMessages((prev) => [...prev, makeMessage("ai", message, true, true)]);
      setChatStatus("error");
      setChatMsg(message);
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