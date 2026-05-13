from pydantic import BaseModel
from typing import Optional


# ── Request ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str
    video_id: Optional[str] = None


# ── Nested schema for sources ─────────────────────────────────────────────────
class ChunkMetadata(BaseModel):
    video_id: str
    title: str
    author: str
    chunk_index: int


# ── Response ──────────────────────────────────────────────────────────────────
class ChatResponse(BaseModel):
    answer: str
    sources: list[ChunkMetadata]
    from_video: bool