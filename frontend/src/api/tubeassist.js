import client from "./client";
//POST /videos/ingest 
export const ingestVideo = (url) =>
  client.post("/videos/ingest", { url });
//* POST /chat/ask
export const askQuestion = (question, videoId) =>
  client.post("/chat/ask", { question, video_id: videoId });