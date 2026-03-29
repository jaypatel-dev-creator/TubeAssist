from app.services.transcript_service import TranscriptService
from app.services.chunking_service import ChunkingService

t = TranscriptService()
c = ChunkingService()

data = t.get_transcript("https://youtube.com/watch?v=NHopJHSlVo4")

docs = c.create_chunks(data)

print("Chunks:", len(docs))
print(docs[0].page_content)
print(docs[0].metadata)
