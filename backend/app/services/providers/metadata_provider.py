
import yt_dlp ##  py library to extract metadata from youtube video


def get_video_metadata(url: str) -> dict:
    ydl_opts = {
        "quiet": True,## to supress all the console output from yt_dlp
        "skip_download": True ## we wont download yt video, just we will extract metadata 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        return {
        
            "title": info.get("title", "Unknown"),
            "author": info.get("uploader", "Unknown")

        }

    except Exception as e:
        print(f"Metadata extraction failed: {e}")
        return { 
    
            "title": "Unknown",
            "author": "Unknown"
        }
    