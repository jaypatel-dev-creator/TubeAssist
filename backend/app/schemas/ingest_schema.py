
from pydantic import BaseModel

#request schema 
class VideoIngestRequest(BaseModel):
    url: str

#response schema 
class VideoIngestSuccess(BaseModel):
    status: str
    video_id: str
    video_title: str
    video_author: str
    chunks_stored: int