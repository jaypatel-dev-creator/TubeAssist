
from pathlib import Path
from app.core.config import VECTOR_STORE, PINECONE_API_KEY, PINECONE_INDEX
from app.services.embedding_service import EmbeddingService


class VectorStoreService:

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_function = embedding_service.get_embedding_model()
        self.store_type = VECTOR_STORE  # "chroma" or "pinecone"

        if self.store_type == "pinecone":
            self.vector_store = self._init_pinecone()
        else:
            self.vector_store = self._init_chroma()

    # ── Chroma (local) ────────────────────────────────────────────────────────
    def _init_chroma(self):
        from langchain_chroma import Chroma

        BASE_DIR = Path(__file__).resolve().parent.parent
        persist_directory = BASE_DIR / "db" / "chroma"# folder where embeddings will be stored  locally 
        persist_directory.mkdir(parents=True, exist_ok=True) ## create embedding storage folder if not exists, if already exists then no error 

        return Chroma(
            collection_name="tube_assist",
            embedding_function=self.embedding_function,  ## due to this function, chroma will automatically embed transcript  on insert and  user query during similarity search
            persist_directory=str(persist_directory),    # chroma expects string path
        )

    # ── Pinecone (production) ─────────────────────────────────────────────────
    def _init_pinecone(self):
        from pinecone import Pinecone, ServerlessSpec
        from langchain_pinecone import PineconeVectorStore

        pc = Pinecone(api_key=PINECONE_API_KEY) #authenticating with pinecone 

        # create index if it doesn't exist
        existing_indexes = [i.name for i in pc.list_indexes()]
        if PINECONE_INDEX not in existing_indexes:
            pc.create_index(
                name=PINECONE_INDEX,
                dimension=3072,       # Gemini embedding-001 default dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1" ## database is being hosted on aws US east 1 
                )
            )
         
        return PineconeVectorStore(
            index_name=PINECONE_INDEX,
            embedding=self.embedding_function,
            pinecone_api_key=PINECONE_API_KEY
        )

    # ── Common interface (same methods for both the backends) 
    def get_vector_store(self): # returns raw vector_store object  (used in retriever_service )
        return self.vector_store

    def add_documents(self, documents):  # adds document in store
        self.vector_store.add_documents(documents)

    def similarity_search(self, query, k, filter=None): ## runs vector search (cosine) and returns top k relevant chunks 
        return self.vector_store.similarity_search(
            query, k=k, filter=filter
        )

    def video_exists(self, video_id: str) -> bool:  ## checks  whether the video is already stored in database 
        if self.store_type == "pinecone":
            return self._video_exists_pinecone(video_id)
        return self._video_exists_chroma(video_id)

    def _video_exists_chroma(self, video_id: str) -> bool: #chroma allows direct lookup with metadata
        results = self.vector_store.get( 
            where={"video_id": video_id}, limit=1 
        )
        return bool(results["ids"])

    def _video_exists_pinecone(self, video_id: str) -> bool: 
        results = self.vector_store.similarity_search(
            query="exists", # just a garbage value because pinecone dosent allow direct lookup with metadatas, it only allow lookup to a  query 
            k=1, 
            filter={"video_id": video_id} # by this filter , if any chunks returns, then video is already stored. 
        )
        return bool(results)
    