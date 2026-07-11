from fastapi import APIRouter
from app.schemas import ChatRequest, ChatResponse
from app.services.rag_service import ask

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/ask", response_model=ChatResponse)
def ask_question(request: ChatRequest) -> dict:
    return ask(
        question=request.question,
        video_id=request.video_id
    )