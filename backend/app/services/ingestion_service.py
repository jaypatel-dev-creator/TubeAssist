
from app.services.transcript_service import TranscriptService
from app.services.chunking_service import ChunkingService
from app.services.vector_store_service import VectorStoreService


class IngestionService:
    

    def __init__(
        self,
        transcript_service: TranscriptService,    # ← injected trancript_service
        chunking_service: ChunkingService,         # ← injected chunking_service
        vector_store_service: VectorStoreService   # ← injected vector_store_service
    ):
        self.transcript_service = transcript_service
        self.chunking_service = chunking_service
        self.vector_store_service = vector_store_service

    def ingest_video(self, url: str):
           # Phase 1: Fetch transcript + metadata
        try:
            transcript_data = self.transcript_service.get_transcript(url)
        except Exception as e:
            # error thrown  and returned to client when extracting transcript failed from both ytdlp and whisper. 
            return {
                "status": "error",
                "message": "Could not fetch transcript. Check if the video exists and is public." 
            }
        
     # Prevent duplicate ingestion
        video_id = transcript_data["video_id"]
        if self.vector_store_service.video_exists(video_id):
            return {  ## returned to client  after user enter already existed video url 
                "status": "already_indexed",
                "video_id": video_id,
                "video_title": transcript_data["title"],
                "video_author": transcript_data["author"]
            }
   # Phase 2: Chunking
        documents = self.chunking_service.create_chunks(transcript_data)

   # Phase 3 + 4: embedding + storing in ChromaDB
        if not documents:
            return {
                "status": "error",
                "message": "Transcript was empty — could not create chunks."
            }

        self.vector_store_service.add_documents(documents)

        # returned to client after successfull ingestion of video. 
        return {
            "status": "success",
            "video_id": video_id,
            "video_title": transcript_data["title"],
            "video_author": transcript_data["author"],
            "chunks_stored": len(documents)
        }
 