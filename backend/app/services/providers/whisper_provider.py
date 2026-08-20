import yt_dlp       ## to extract audio from video
import tempfile      ## to save the audio file extracted from yt video inside OS temporary directory rather than project folder
from pathlib import Path
from groq import Groq

from app.core.config import get_settings
from app.core.exceptions import TranscriptFetchException


# download_audio() uses yt-dlp to download audio as mp3 to feed to Groq Whisper API
def download_audio(url: str) -> Path:
    temp_dir = Path(tempfile.gettempdir())
    output = str(temp_dir / "temp_audio.%(ext)s")

    ydl_opts = {
        "format": "mp3/bestaudio/best",  # prefer mp3 — Groq requires a supported format
        "outtmpl": output,               # location of file saving
        "quiet": True,                   # dont output logs
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",     # convert to mp3 if not already
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])              # downloading the audio file

    # find the downloaded mp3 file
    audio_files = list(temp_dir.glob("temp_audio.*"))
    if not audio_files:
        raise TranscriptFetchException()  # surfaces cleanly as 422 to the user

    return audio_files[0]


# feeds audio file from download_audio() to Groq Whisper API, returns full transcript, deletes temp file.
def get_whisper_transcript(url: str) -> str:
    audio_path = download_audio(url)  # downloading audio

    try:
        client = Groq(api_key=get_settings().groq_api_key)

        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",  # best price-to-performance on Groq free tier
                language="en",                   # explicitly set to improve accuracy and latency
                response_format="text",          # returns plain string directly
                temperature=0.0                  # deterministic output
            )

        return transcription  # response_format="text" returns the transcript string directly

    finally:
        try:
            audio_path.unlink()  # delete temp audio file from OS temporary directory
        except Exception:
            pass  # cleanup failure is not important enough to crash the whole thing