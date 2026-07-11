from app.services.transcript_service import get_transcript
from app.services.chunking_service import create_chunks
from app.services.vector_store_service import video_exists, add_documents


def ingest_video(url: str) -> dict:
    # Phase 1: Fetch transcript + metadata
    try:
        transcript_data = get_transcript(url)
    except Exception:
        return {
            "status": "error",
            "message": "Could not fetch transcript. Check if the video exists and is public."
        }

    # Prevent duplicate ingestion
    video_id = transcript_data["video_id"]
    if video_exists(video_id):
        return {
            "status": "already_indexed",
            "video_id": video_id,
            "video_title": transcript_data["title"],
            "video_author": transcript_data["author"]
        }

    # Phase 2: Chunking
    documents = create_chunks(transcript_data)

    # Phase 3 + 4: Embed + store
    if not documents:
        return {
            "status": "error",
            "message": "Transcript was empty — could not create chunks."
        }

    add_documents(documents)

    return {
        "status": "success",
        "video_id": video_id,
        "video_title": transcript_data["title"],
        "video_author": transcript_data["author"],
        "chunks_stored": len(documents)
    }