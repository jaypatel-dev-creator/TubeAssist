## Conditional Retrieval with Metadata Filtering
## - If the user provides a video link → restrict retrieval using video_id for context-specific answers => Scoped retrieval / scoped search
## - If no video is provided → perform global search (full vector search) across all indexed data => global retrieval / global search
## With current implementation, for each user query and follow up question always video_id will be passed,
## so global search block won't fire. In future we may allow search across all ingested videos, then global search will work.

from app.services.vector_store_service import VectorStoreService
from app.core.config import VECTOR_STORE


class RetrieverService:

    def __init__(self, vector_store_service: VectorStoreService):  # DI for vector_store service
        self.vector_store = vector_store_service.get_vector_store()
    #currently , retrieve wont be used , retrieve_with_scores will be used , still it is kept for future  use — e.g. if we  want retrieval without score filtering
    # ── Scoped / global retrieval ─────────────────────────────────────────────
    def retrieve(self, query: str, k: int = 6, video_id: str | None = None):
        if video_id is not None:
            ## scoped retrieval — only chunks from this video (top k chunks)
            results = self.vector_store.similarity_search(
                query=query, k=k, filter={"video_id": video_id}
            )
        else:
            ## global retrieval — all indexed videos
            results = self.vector_store.similarity_search(
                query=query, k=k
            )
        return results


    
    def retrieve_with_scores(self, query: str, k: int = 6, video_id: str | None = None):
        if video_id is not None:
            ## scoped retrieval with scores
            results = self.vector_store.similarity_search_with_score(
                query=query, k=k, filter={"video_id": video_id}
            )
        else:
            ## global retrieval with scores
            results = self.vector_store.similarity_search_with_score(
                query=query, k=k
            )

        # ── Normalize Pinecone scores to distance scale ───────────────────────
        # ChromaDB → distance (0 to 2), lower = more relevant → no change needed
        # Pinecone → similarity (0 to 1), higher = more relevant → will be converted to distance. 
        if VECTOR_STORE == "pinecone":
            results = [(doc, 1 - score) for doc, score in results] ## converting  to distance 

        return results  
    

        # Score scale after normalization (same for both backends):
    #   lower = more relevant
    #   0.0   = identical
    #   0.7+  = likely irrelevant → triggers LLM fallback in RAGService