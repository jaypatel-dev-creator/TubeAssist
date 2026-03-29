import yt_dlp
import re
import tempfile
from pathlib import Path

def get_youtube_transcript(video_id:str) -> str:
    temp_dir = Path(tempfile.gettempdir())

    ydl_opts = {
        'writeautomaticsub': True,#download auto generated captions 
        'writesubtitles': True,# download human subtitles (if available)
        'skip_download': True,# dont download audio / video 
        'subtitlesformat': 'vtt',# spcfify format of subtitle 
        'subtitleslangs': ['en'],# download only english subtitle
        'outtmpl': str(temp_dir / f'temp_{video_id}'),# subtitle file name 
        'quiet': True, # dont print logs in console 
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(video_id)

    vtt_files = list(temp_dir.glob(f'temp_{video_id}*.vtt'))

    if not vtt_files:
        raise Exception("No captions found")

    with open(vtt_files[0], 'r', encoding='utf-8') as f:
        raw = f.read()

    vtt_files[0].unlink()  # delete temp subtitle file 
    return _parse_vtt(raw) # return cleaned subtitles 

def _parse_vtt(vtt_text: str) -> str:
    lines = vtt_text.split('\n')
    text_lines = []
    seen = set()

    # Patterns to skip
    SKIP_PATTERNS = [
        r'^WEBVTT',
        r'^Kind:',
        r'^Language:',
        r'^Transcriber:',
        r'^Reviewer:',
        r'-->',                          # timestamp lines
        r'^\d+$',                        # bare cue numbers
        r'^align:',                      # positioning metadata
        r'^\s*$',                        # blank lines
    ]
    skip_re = re.compile('|'.join(SKIP_PATTERNS))

    for line in lines:
        line = line.strip()

        if skip_re.search(line):
            continue

        # Remove all inline tags: <c>, </c>, <00:00:01.234>, <b>, etc.
        clean = re.sub(r'<[^>]+>', '', line).strip()

        # Decode HTML entities just in case
        clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')

        if clean and clean not in seen:
            seen.add(clean)
            text_lines.append(clean)

    merged = ' '.join(text_lines)
    merged = re.sub(r'\s+', ' ', merged).strip()
    return merged