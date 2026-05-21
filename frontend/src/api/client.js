import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000", // backend url 
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 180000, // 3 minutes — Whisper can take long
});

export default client;