from fastapi import APIRouter
from app.schemas import VideoIngestRequest
from app.services.ingestion_service import ingest_video

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post("/ingest")
def ingest_video_route(request: VideoIngestRequest) -> dict:
    return ingest_video(request.url)