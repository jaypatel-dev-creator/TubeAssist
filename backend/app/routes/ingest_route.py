from fastapi import APIRouter
from app.schemas import VideoIngestRequest, VideoIngestSuccess
from app.services.ingestion_service import ingest_video

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post("/ingest", response_model=VideoIngestSuccess)
def ingest_video_route(request: VideoIngestRequest) -> dict:
    return ingest_video(request.url)
