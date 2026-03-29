from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.ingestion_service import IngestionService
from app.dependencies import get_ingestion_service
router = APIRouter(prefix="/videos", tags=["Videos"])

## ingestion service will be utilized in ingest_route
class VideoRequest(BaseModel):
    url: str

@router.post("/ingest")
def ingest_video(
    request: VideoRequest,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> dict:

    result = ingestion_service.ingest_video(request.url)
    return result