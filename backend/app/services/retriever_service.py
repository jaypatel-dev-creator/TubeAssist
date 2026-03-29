# from app.services.vector_store_service import VectorStoreService

## Conditional Retrieval with Metadata Filtering
## - If the user provides a video link → restrict retrieval using video_id for context-specific answers => Scoped retrieval/ scoped search 
## - If no video is provided → perform global search (full vector search)across all indexed data (general-purpose QA) => global retrieval /global search 
## with current implementation , for each user query  and follow up question always video id will be passed to the llm , so globalsearch block wont , in future we may allow to search across all ingested videos, then global search will work


from app.services.vector_store_service import VectorStoreService


class RetrieverService:

    def __init__(self, vector_store_service: VectorStoreService):  # DI for vector_store service 
        self.vector_store = vector_store_service.get_vector_store()
    ## top 4 relevant documents will be returned 
    def retrieve(self, query: str, k: int = 4, video_id: str | None = None):
        ## scoped retrieval
        if video_id is not None:
            results = self.vector_store.similarity_search(
                query=query, k=k, filter={"video_id": video_id}
            )
        else: 
            ## global retrieval 
            results = self.vector_store.similarity_search(
                query=query, k=k
            )
        return results
    