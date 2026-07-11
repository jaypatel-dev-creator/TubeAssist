
from pydantic import BaseModel


class VideoIngestRequest(BaseModel):
    url: str


class VideoIngestSuccess(BaseModel):
    status: str
    video_id: str
    video_title: str
    video_author: str
    chunks_stored: int