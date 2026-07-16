from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import get_settings


# module level singleton 
_embeddings: GoogleGenerativeAIEmbeddings | None = None


def get_embedding_model() -> GoogleGenerativeAIEmbeddings:
    if _embeddings is None:
        raise RuntimeError("Embedding model not initialized. Call init_services() on startup.")
    return _embeddings


def init_embedding_model() -> None:
    global _embeddings
    _embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=get_settings().gemini_api_key,
        task_type="retrieval_document"
    )