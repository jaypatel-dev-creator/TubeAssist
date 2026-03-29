import yt_dlp       ## to extract audio from video
import tempfile      ## to save the audio file extracted from yt video inside OS temporary directory rather than project folder
from pathlib import Path

# ── Lazy loading — Whisper model only loads when actually needed ──────────────
# This prevents RAM consumption at server startup on Render free tier (512MB limit)
# If yt-dlp captions succeed, Whisper never loads and zero RAM is consumed
_model = None

def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel  # ← imported only when needed
        _model = WhisperModel("base", device="cpu")
    return _model


def download_audio(url: str) -> Path:
    temp_dir = Path(tempfile.gettempdir())          # getting temp directory
    output = str(temp_dir / "temp_audio.%(ext)s")  # where to save file along with extension

    ydl_opts = {
        "format": "bestaudio/best",  # download the best audio quality
        "outtmpl": output,           # where to save file
        "quiet": True                # dont output logs
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])          # downloading the audio file

    # find whatever audio file was downloaded (.webm, .m4a, .mp3)
    audio_files = list(temp_dir.glob("temp_audio.*"))
    if not audio_files:
        raise Exception("Audio download failed")

    return audio_files[0]


def get_whisper_transcript(url: str) -> str:
    audio_path = download_audio(url)  # downloading audio

    try:
        segments, _ = _get_model().transcribe(str(audio_path))  # ← loads model only here
        text = " ".join(segment.text for segment in segments)   # joining all extracted segments into single paragraph
        return text

    finally:
        try:
            audio_path.unlink()  # delete temp audio file from OS temporary directory
        except Exception:
            pass