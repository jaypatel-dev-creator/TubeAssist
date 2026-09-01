from pathlib import Path
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.embedding_service import get_embedding_model
from app.core.exceptions import VectorStoreException

logger = get_logger(__name__)


def _init_chroma():
    from langchain_chroma import Chroma

    BASE_DIR = Path(__file__).resolve().parent.parent
    persist_directory = BASE_DIR / "db" / "chroma"
    persist_directory.mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name="tube_assist",
        embedding_function=get_embedding_model(),
        persist_directory=str(persist_directory),
    )


def _init_pinecone():
    from pinecone import Pinecone, ServerlessSpec
    from langchain_pinecone import PineconeVectorStore

    settings = get_settings()
    pc = Pinecone(api_key=settings.pinecone_api_key)

    existing_indexes = [i.name for i in pc.list_indexes()]
    if settings.pinecone_index not in existing_indexes:
        pc.create_index(
            name=settings.pinecone_index,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

    return PineconeVectorStore(
        index_name=settings.pinecone_index,
        embedding=get_embedding_model(),
        pinecone_api_key=settings.pinecone_api_key
    )

# module level variable (singleton) that will contain either chroma or pinecone db
_vector_store = None


def get_vector_store():
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Call init_vector_store() on startup.")
    return _vector_store


def init_vector_store() -> None:
    global _vector_store
    if get_settings().vector_store == "pinecone":
        _vector_store = _init_pinecone()
    else:
        _vector_store = _init_chroma()


# Public functions (called by ingestion_service and retriever_service)
def add_documents(documents) -> None:
    try:
        get_vector_store().add_documents(documents)
    except Exception as e:
        logger.error("add_documents failed: %s", str(e))
        raise VectorStoreException("Failed to store documents. Please try again later.")


def video_exists(video_id: str) -> bool:
    try:
        if get_settings().vector_store == "pinecone":
            return _video_exists_pinecone(video_id)
        return _video_exists_chroma(video_id)
    except Exception as e:
        logger.error("video_exists check failed: %s", str(e))
        raise VectorStoreException("Failed to check video existence. Please try again later.")


# private functions
def _video_exists_chroma(video_id: str) -> bool:
    results = get_vector_store().get(
        where={"video_id": video_id}, limit=1
    )
    return bool(results["ids"])


def _video_exists_pinecone(video_id: str) -> bool:
    results = get_vector_store().similarity_search(
        query="exists",
        k=1,
        filter={"video_id": video_id}
    )
    return bool(results)