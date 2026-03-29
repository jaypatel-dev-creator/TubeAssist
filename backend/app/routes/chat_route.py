
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.services.rag_service import RAGService
from app.dependencies import get_rag_service

router = APIRouter(prefix="/chat", tags=["Chat"])



class QuestionRequest(BaseModel):
    question: str
    video_id: str | None = None

@router.post("/ask")
def ask_question(
    request: QuestionRequest,
    rag_service: RAGService = Depends(get_rag_service)  # ← injected (parameter injection for routes )
) -> dict:
    response = rag_service.ask(
        question=request.question,
        video_id=request.video_id
    )
    return response