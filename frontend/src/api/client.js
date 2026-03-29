import axios from "axios";

// ─── Base instance ────────────────────────────────────────────────────────────
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 180000, // 3 minutes for timeout 
});

// ─── Request interceptor ──────────────────────────────────────────────────────
// Attach auth token here if you add login later
client.interceptors.request.use(
  (config) => {
    // const token = localStorage.getItem("token");
    // if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response interceptor ─────────────────────────────────────────────────────
// 1. Unwraps response.data so callers get payload directly
// 2. Normalizes all errors into a plain Error with a clean message
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message =
      error.response?.data?.detail  ||  // FastAPI validation / custom errors
      error.response?.data?.message ||  // generic JSON error
      error.message                 ||  // axios network / timeout error
      "Something went wrong.";

    return Promise.reject(new Error(message));
  }
);

export default client;