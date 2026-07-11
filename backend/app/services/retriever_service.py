from app.core.config import VECTOR_STORE
from app.services.vector_store_service import get_vector_store


def retrieve_with_scores(query: str, k: int = 6, video_id: str | None = None) -> list:
    vector_store = get_vector_store()

    if video_id is not None:
        results = vector_store.similarity_search_with_score(
            query=query, k=k, filter={"video_id": video_id}
        )
    else:
        results = vector_store.similarity_search_with_score(
            query=query, k=k
        )

    # normalize Pinecone cosine similarity to cosine distance
    if VECTOR_STORE == "pinecone":
        results = [(doc, 1 - score) for doc, score in results]

    return results