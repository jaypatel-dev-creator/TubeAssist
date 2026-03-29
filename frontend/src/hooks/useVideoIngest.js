import { useState, useCallback } from "react";
import { ingestVideo } from "../api/tubeassist";

// ─── Hook ─────────────────────────────────────────────────────────────────────
/**
 * useVideoIngest
 *
 * Handles everything related to loading a YouTube video.
 *
 * Returns:
 *   videoId      — video_id returned by backend after ingestion
 *   videoTitle   — video_title returned by backend after ingestion
 *   isIngesting  — true while backend is processing
 *   ingestStatus — "processing" | "success" | "error" | null
 *   ingestMsg    — message string for StatusBar
 *   handleIngest — call this with a YouTube URL to start ingestion
 *   reset        — clears all state (called when new video is loaded)
 */
export default function useVideoIngest() {
  const [videoId,      setVideoId]      = useState("");
  const [videoTitle,   setVideoTitle]   = useState("");
  const [isIngesting,  setIsIngesting]  = useState(false);
  const [ingestStatus, setIngestStatus] = useState(null);
  const [ingestMsg,    setIngestMsg]    = useState("");

  const reset = useCallback(() => {
    setVideoId("");
    setVideoTitle("");
    setIngestStatus(null);
    setIngestMsg("");
  }, []);

  const handleIngest = useCallback(async (url) => {
    setVideoId("");
    setVideoTitle("");
    setIsIngesting(true);
    setIngestStatus("processing");
    setIngestMsg("Processing video…");

    try {
      const data = await ingestVideo(url);

      // backend returned a handled error (e.g. fake video, empty transcript)
      if (data.status === "error") {
        setIngestStatus("error");
        setIngestMsg(data.message || "Something went wrong.");
        return;  // stop here — don't set videoTitle or videoId
      }

      // status: "success" or "already_indexed" — both are valid
      setVideoId(data.video_id || "");
      setVideoTitle(data.video_title || "Untitled Video");
      setIngestStatus("success");
      setIngestMsg(
        data.status === "already_indexed"
          ? "Already indexed — start asking questions!"
          : "Video ready — start asking questions!"
      );
    } catch (err) {
      // network error, timeout, or unhandled backend exception
      setVideoId("");
      setIngestStatus("error");
      setIngestMsg(err.message || "Something went wrong.");
    } finally {
      setIsIngesting(false);
    }
  }, []);

  return {
    videoId,
    videoTitle,
    isIngesting,
    ingestStatus,
    ingestMsg,
    handleIngest,
    reset,
  };
}