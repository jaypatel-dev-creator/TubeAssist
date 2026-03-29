from app.services.embedding_service import EmbeddingService

service = EmbeddingService()

embedding_model = service.get_embedding_model()

texts=[
    "Ai is transforming the world" ,
    "Paris is capital of France"
]

embeddings = embedding_model.embed_documents(texts)



print("Number of embeddings:", len(embeddings))
print("Embedding length:", len(embeddings[0]))
