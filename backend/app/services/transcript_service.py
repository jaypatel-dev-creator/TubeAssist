from app.services.providers.youtube_provider import get_youtube_transcript
from app.services.providers.whisper_provider import get_whisper_transcript
from app.services.providers.metadata_provider import get_video_metadata

import re


class TranscriptService:

    @staticmethod
    # method to extract video id from the url that user will pass 
    def extract_video_id(url: str) -> str:

        patterns = [
            r"v=([^&]+)",
            r"youtu\.be/([^?]+)"
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise ValueError("Invalid YouTube URL")


    @staticmethod
    # method to get transcript from the url 
    def get_transcript(url: str) -> dict:
         # first extract respective video id from the url passed 
        video_id = TranscriptService.extract_video_id(url)

        try:

            print("Using yt-dlp for caption extraction...")
            transcript_text = get_youtube_transcript(video_id)
            if not transcript_text or len(transcript_text.strip()) < 50:
                raise Exception("Empty transcript")

        except Exception:

            print("Fallback to Whisper...")
            transcript_text = get_whisper_transcript(url)
  
      ## getting title and author metadata  
        metadata = get_video_metadata(url)

        return {
            "video_id": video_id, 
            "title": metadata["title"],
            "author": metadata["author"],
            "transcript": transcript_text
        }
    # final video-id metadata comes from transcript_service, title and author comes from metadata_provider
