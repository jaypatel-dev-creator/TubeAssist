from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import GEMINI_API_KEY

class EmbeddingService:
    def __init__(self):
        self.model_name = "models/gemini-embedding-001"
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=GEMINI_API_KEY,
            task_type="retrieval_document"
        )

    def get_embedding_model(self):
        return self.embeddings