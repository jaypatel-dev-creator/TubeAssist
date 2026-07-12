from app.services.transcript_service import get_transcript
from app.services.chunking_service import create_chunks
from app.services.vector_store_service import video_exists, add_documents
from app.core.exceptions import VideoAlreadyIndexedException, EmptyTranscriptException


def ingest_video(url: str) -> dict:
    # Phase 1: Fetch transcript + metadata
    # InvalidURLException / TranscriptFetchException propagate up from transcript_service
    transcript_data = get_transcript(url)

    # Phase 2: Duplicate check
    video_id = transcript_data["video_id"]
    if video_exists(video_id):
        raise VideoAlreadyIndexedException(
            video_id=video_id,
            video_title=transcript_data["title"],
            video_author=transcript_data["author"]
        )

    # Phase 3: Chunking
    documents = create_chunks(transcript_data)

    if not documents:
        raise EmptyTranscriptException()

    # Phase 4: Embed + store
    add_documents(documents)

    return {
        "status": "success",
        "video_id": video_id,
        "video_title": transcript_data["title"],
        "video_author": transcript_data["author"],
        "chunks_stored": len(documents)
    }