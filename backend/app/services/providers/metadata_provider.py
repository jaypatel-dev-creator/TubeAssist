import yt_dlp


def get_video_metadata(url: str) -> dict:
    ydl_opts = {
        "quiet": True,
        "skip_download": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info.get("title", "Unknown"),
        "author": info.get("uploader", "Unknown")
    }