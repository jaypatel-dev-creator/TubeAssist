from app.dependencies import (
    get_ingestion_service,
    get_vector_store_service,
    get_embedding_service,
    get_transcript_service,
    get_chunking_service
)

# reuse the same provider functions
## here both ingestion and duplicate ingestion are tested 
service = get_ingestion_service()

url = "https://youtu.be/1aA1WGON49E?si=59WyQTXQmCgbnniM"

print("First ingestion:")
print(service.ingest_video(url))

print("\nSecond ingestion:")
print(service.ingest_video(url))