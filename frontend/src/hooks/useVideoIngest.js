import { useState, useCallback } from "react";
import { ingestVideo } from "../api/tubeassist";

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
      const response = await ingestVideo(url);
      const data = response.data;  // manual unwrap

      if (data.status === "error") {
        setIngestStatus("error");
        setIngestMsg(data.message || "Something went wrong.");
        return;
      }

      setVideoId(data.video_id || "");
      setVideoTitle(data.video_title || "Untitled Video");
      setIngestStatus("success");
      setIngestMsg(
        data.status === "already_indexed"
          ? "Already indexed — start asking questions!"
          : "Video ready — start asking questions!"
      );
    } catch (err) {
      const message = err.response?.data?.detail ||
                      err.response?.data?.message ||
                      err.message ||
                      "Something went wrong.";
      setVideoId("");
      setIngestStatus("error");
      setIngestMsg(message);
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