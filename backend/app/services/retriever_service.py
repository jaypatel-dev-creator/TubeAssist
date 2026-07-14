from app.core.config import get_settings
from app.services.vector_store_service import get_vector_store


def retrieve_with_scores(query: str, k: int = 6, video_id: str | None = None) -> list:
    vector_store = get_vector_store()

    if video_id is not None:
        #scoped retrieval 
        results = vector_store.similarity_search_with_score(
            query=query, k=k, filter={"video_id": video_id}
        )
    else:#global retrieval 
        results = vector_store.similarity_search_with_score(
            query=query, k=k
        )

    # normalize Pinecone cosine similarity to cosine distance
    if get_settings().vector_store == "pinecone":
        results = [(doc, 1 - score) for doc, score in results]

    return results