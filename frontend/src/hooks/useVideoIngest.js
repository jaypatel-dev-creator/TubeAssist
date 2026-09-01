import { useState, useCallback } from "react";
import { ingestVideo } from "../api/tubeassist";

export default function useVideoIngest() {
  const [videoId,      setVideoId]      = useState("");
  const [videoTitle,   setVideoTitle]   = useState("");
  const [sessionId,    setSessionId]    = useState("");
  const [isIngesting,  setIsIngesting]  = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [ingestMsg,    setIngestMsg]    = useState("");

  const reset = useCallback(() => {
    setVideoId("");
    setVideoTitle("");
    setSessionId("");
    setIngestStatus(null);
    setIngestMsg("");
  }, []);

  const handleIngest = useCallback(async (url) => {
    setVideoId("");
    setVideoTitle("");
    setSessionId("");
    setIsIngesting(true);
    setIngestStatus("processing");
    setIngestMsg("Processing video…");

    try {
      const response = await ingestVideo(url);
      const data = response.data;

      setVideoId(data.video_id || "");
      setVideoTitle(data.video_title || "Untitled Video");
      setSessionId(crypto.randomUUID());
      setIngestStatus("success");
      setIngestMsg("Video ready — start asking questions!");

    } catch (err) {
      const status = err.response?.status;
      const data = err.response?.data;

      if (status === 409 && data?.video_id) {
        // Video already indexed — restore state and allow chat
        // Still generate a fresh session_id so history is clean
        setVideoId(data.video_id);
        setVideoTitle(data.video_title || "Untitled Video");
        setSessionId(crypto.randomUUID());
        setIngestStatus("success");
        setIngestMsg(`'${data.video_title}' is already indexed — start asking questions!`);
      } else {
        const message = data?.error ||
                        data?.detail ||
                        err.message ||
                        "Something went wrong.";
        setVideoId("");
        setSessionId("");
        setIngestStatus("error");
        setIngestMsg(message);
      }
    } finally {
      setIsIngesting(false);
    }
  }, []);

  return {
    videoId,
    videoTitle,
    sessionId,
    isIngesting,
    ingestStatus,
    ingestMsg,
    handleIngest,
    reset,
  };
}