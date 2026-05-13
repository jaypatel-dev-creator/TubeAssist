from pydantic import BaseModel


# ── Request ───────────────────────────────────────────────────────────────────
class VideoIngestRequest(BaseModel):
    url: str


# ── Response variants ─────────────────────────────────────────────────────────
class VideoIngestSuccess(BaseModel):
    status: str        # "success"
    video_id: str
    video_title: str
    video_author: str
    chunks_stored: int


class VideoAlreadyIndexed(BaseModel):
    status: str        # "already_indexed"
    video_id: str
    video_title: str
    video_author: str


class VideoIngestError(BaseModel):
    status: str        # "error"
    message: str