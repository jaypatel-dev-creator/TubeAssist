
from app.services.vector_store_service import VectorStoreService
from app.core.config import VECTOR_STORE


class RetrieverService:

    def __init__(self, vector_store_service: VectorStoreService):  
        self.vector_store = vector_store_service.get_vector_store()
   
    
    def retrieve_with_scores(self, query: str, k: int = 6, video_id: str | None = None):
        if video_id is not None:
            ## scoped retrieval with scores
            results = self.vector_store.similarity_search_with_score(
                query=query, k=k, filter={"video_id": video_id}
            )
        else:
            ## global retrieval with scores (not used in current implementation, kept for future use )
            results = self.vector_store.similarity_search_with_score(
                query=query, k=k
            )

    #normalizing pinecone score (cosine similarity) to cosine distance. 
        if VECTOR_STORE == "pinecone":
            results = [(doc, 1 - score) for doc, score in results] 

        return results  
    

 