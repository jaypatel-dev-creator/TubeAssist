from pydantic import BaseModel


# request schema 
class VideoIngestRequest(BaseModel):
    url: str

##response bodies 
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
    # since ingestion serevice returns 3 different response bodies, so response bodies wont be implemented for ingest_route. 