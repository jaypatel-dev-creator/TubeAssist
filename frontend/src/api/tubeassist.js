import client from "./client";

// ─── Ingest ───────────────────────────────────────────────────────────────────
/**
 * POST /videos/ingest
 * Sends a YouTube URL to the backend for transcript fetching + embedding.
 *
 * @param {string} url — validated YouTube URL
 * @returns {Promise<{ title: string, video_id: string }>}
 */
export const ingestVideo = (url) =>
  client.post("/videos/ingest", { url });

// ─── Chat ─────────────────────────────────────────────────────────────────────
/**
 * POST /chat/ask
 * Sends a question about the currently ingested video.
 *
 * @param {string} question  — user's question
 * @param {string} videoId   — video_id returned from ingestVideo
 * @returns {Promise<{ answer: string }>}
 */
export const askQuestion = (question, videoId) =>
  client.post("/chat/ask", { question, video_id: videoId });