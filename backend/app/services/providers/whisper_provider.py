import yt_dlp       ## to extract audio from video
import tempfile      ## to save the audio file extracted from yt video inside OS temporary directory rather than project folder
from pathlib import Path

# ── Lazy loading — Whisper model only loads when actually needed ──────────────
# This prevents RAM consumption at server startup on Render free tier (512MB limit) along with zero RAM consumption locally when no whisper fallback is triggered
_model = None

def _get_model():
    global _model #tells python to modify the global _model variable , instead of creating a local _model variable. 
    if _model is None:
        from faster_whisper import WhisperModel 
        _model = WhisperModel("base", device="cpu") # we are using faster whisper base model
    return _model



# download_audio() uses ytdlp to download best audio to feed to faster whisper 
def download_audio(url: str) -> Path:
    temp_dir = Path(tempfile.gettempdir())          # getting temp directory
    output = str(temp_dir / "temp_audio.%(ext)s") # saving audio file in temp dir

    ydl_opts = {
        "format": "bestaudio/best",  # download the best audio quality
        "outtmpl": output,           # location of file saving 
        "quiet": True                # dont output logs
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])          # downloading the audio file

    # find whatever audio file was downloaded (.webm, .m4a, .mp3)
    audio_files = list(temp_dir.glob("temp_audio.*"))
    if not audio_files:
        raise Exception("Audio download failed")

    return audio_files[0]



# feeds that audio file from download_audio()  to FasterWhisper, joins all segments into one paragraph, deletes temp audio file.
def get_whisper_transcript(url: str) -> str:
    audio_path = download_audio(url)  # downloading audio

    try:
        segments, _ = _get_model().transcribe(str(audio_path))  # loads model only here , transcribe is function from faster wihsper that generates tranascript from audio file 
        text = " ".join(segment.text for segment in segments)   # joining all extracted segments into single paragraph
        return text

    finally:
        try:
            audio_path.unlink()  # delete temp audio file from OS temporary directory
        except Exception:
            pass # if any exception occurs in deleting the temp audio file, then dont throw error and crash, ignore it and move on because cleanup failure is not important to crash the whole thing 