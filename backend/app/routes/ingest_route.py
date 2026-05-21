from fastapi import APIRouter, Depends
from app.schemas import VideoIngestRequest
from app.services.ingestion_service import IngestionService
from app.dependencies import get_ingestion_service

router = APIRouter(prefix="/videos", tags=["Videos"])


@router.post("/ingest")
def ingest_video(
    request: VideoIngestRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service)# that : specifies that ingestion_service is object of IngestionService so later you call methods of IngestionService with ingestion_service 
) -> dict:
    result = ingestion_service.ingest_video(request.url)
    return result
    