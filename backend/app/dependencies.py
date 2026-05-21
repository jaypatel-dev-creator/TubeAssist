
from functools import lru_cache
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
from app.services.retriever_service import RetrieverService
from app.services.memory_service import MemoryService
from app.services.transcript_service import TranscriptService
from app.services.chunking_service import ChunkingService
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGService


# ── Singletons 

@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()

@lru_cache
def get_vector_store_service() -> VectorStoreService:
    return VectorStoreService(
        embedding_service=get_embedding_service()
    )

@lru_cache
def get_retriever_service() -> RetrieverService:
    return RetrieverService(
        vector_store_service=get_vector_store_service()
    )

@lru_cache
def get_transcript_service() -> TranscriptService:
    return TranscriptService()

@lru_cache
def get_chunking_service() -> ChunkingService:
    return ChunkingService()


# ── Request-scoped 

def get_memory_service() -> MemoryService:
    return MemoryService()

def get_ingestion_service() -> IngestionService:
    return IngestionService(
        transcript_service=get_transcript_service(),
        chunking_service=get_chunking_service(),
        vector_store_service=get_vector_store_service()
    )

def get_rag_service() -> RAGService:
    return RAGService(
        retriever_service=get_retriever_service(),
        memory_service=get_memory_service()
    )
