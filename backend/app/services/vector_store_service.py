from pathlib import Path
from app.core.config import VECTOR_STORE, PINECONE_API_KEY, PINECONE_INDEX
from app.services.embedding_service import get_embedding_model


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

    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing_indexes = [i.name for i in pc.list_indexes()]
    if PINECONE_INDEX not in existing_indexes:
        pc.create_index(
            name=PINECONE_INDEX,
            dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )

    return PineconeVectorStore(
        index_name=PINECONE_INDEX,
        embedding=get_embedding_model(),
        pinecone_api_key=PINECONE_API_KEY
    )


# ── Singleton ──────────────────────────────────────────────────────────────────
_vector_store = None


def get_vector_store():
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Call init_services() on startup.")
    return _vector_store


def init_vector_store() -> None:
    global _vector_store
    if VECTOR_STORE == "pinecone":
        _vector_store = _init_pinecone()
    else:
        _vector_store = _init_chroma()


# ── Public API (called by ingestion_service and retriever_service) ─────────────
def add_documents(documents) -> None:
    get_vector_store().add_documents(documents)


def video_exists(video_id: str) -> bool:
    if VECTOR_STORE == "pinecone":
        return _video_exists_pinecone(video_id)
    return _video_exists_chroma(video_id)


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