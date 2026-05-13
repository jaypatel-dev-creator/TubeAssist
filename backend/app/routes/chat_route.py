from fastapi import APIRouter, Depends
from app.schemas import ChatRequest, ChatResponse
from app.services.rag_service import RAGService
from app.dependencies import get_rag_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/ask", response_model=ChatResponse)
def ask_question(
    request: ChatRequest,
    rag_service: RAGService = Depends(get_rag_service)  # ← injected
) -> dict:
    response = rag_service.ask(
        question=request.question,
        video_id=request.video_id
    )
    return response