from pydantic import BaseModel


# request schema 
class ChatRequest(BaseModel):
    question: str
    video_id: str | None = None
    session_id: str | None = None

# response 
# sources contains a list of metadata objects — each validated separately via ChunkMetadata
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