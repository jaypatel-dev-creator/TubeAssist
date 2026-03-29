from app.services.transcript_service import TranscriptService
from app.services.chunking_service import ChunkingService
from app.dependencies import get_vector_store_service

t = TranscriptService()
c = ChunkingService()
v = get_vector_store_service()

data = t.get_transcript("https://youtu.be/1aA1WGON49E?si=59WyQTXQmCgbnniM")
docs = c.create_chunks(data)

v.add_documents(docs)

print("Stored successfully")

## for rag service no unit testing , direct integration testing using swagger 
# "I tested the RAG service end-to-end using FastAPI's built-in Swagger UI at /docs. I first hit POST /videos/ingest with a YouTube URL, copied the video_id from the response, then hit POST /chat/ask with a question and that video_id. This validated the full pipeline — transcript extraction, chunking, embedding, retrieval, and LLM response — in one shot."