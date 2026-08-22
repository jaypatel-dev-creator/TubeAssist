import yt_dlp       ## to extract audio from video
import tempfile      ## to save the audio file extracted from yt video inside OS temporary directory rather than project folder
from pathlib import Path
from groq import Groq

from app.core.config import get_settings
from app.core.exceptions import TranscriptFetchException


MAX_AUDIO_SIZE_BYTES = 24 * 1024 * 1024  # 24MB — safe margin under Groq's 25MB free tier limit


# download_audio() uses yt-dlp to download audio as mp3 at 64kbps to feed to Groq Whisper API
# 64kbps keeps file size ~28MB/hour — videos up to ~50 min stay safely under the 25MB Groq limit
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
            "preferredquality": "64",    # cap at 64kbps — keeps file small for Groq 25MB limit
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])              # downloading the audio file

    # find the downloaded mp3 file
    audio_files = list(temp_dir.glob("temp_audio.*"))
    if not audio_files:
        raise TranscriptFetchException()  # surfaces cleanly as 422 to the user

    audio_path = audio_files[0]

    # safety net — if file still exceeds 24MB, raise a clear error before hitting Groq's 25MB limit
    if audio_path.stat().st_size > MAX_AUDIO_SIZE_BYTES:
        audio_path.unlink()  # clean up before raising
        raise TranscriptFetchException(
            "Video is too long for audio transcription. Try a video under 45 minutes."
        )

    return audio_path


# feeds audio file from download_audio() to Groq Whisper API, returns full transcript, deletes temp file.
def get_whisper_transcript(url: str) -> str:
    audio_path = download_audio(url)  # downloading audio

    try:
        client = Groq(api_key=get_settings().groq_api_key)

        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",  # best price-to-performance on Groq free tier
                response_format="text",          # returns plain string directly
                temperature=0.0                  # deterministic output
                # language not set — whisper-large-v3-turbo auto-detects, supports multilingual content
            )

        return transcription  # response_format="text" returns the transcript string directly

    finally:
        try:
            audio_path.unlink()  # delete temp audio file from OS temporary directory
        except Exception:
            pass  # cleanup failure is not important enough to crash the whole thing