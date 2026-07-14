from fastapi import Request
from fastapi.responses import JSONResponse


# ── Base Exception ─────────────────────────────────────────────────────────────
class TubeAssistException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ── Domain Exceptions ──────────────────────────────────────────────────────────
class InvalidURLException(TubeAssistException):
    def __init__(self, url: str):
        super().__init__(
            message=f"Invalid YouTube URL: '{url}'",
            status_code=422
        )


class TranscriptFetchException(TubeAssistException):
    def __init__(self):
        super().__init__(
            message="Could not fetch transcript. Check if the video exists and is public.",
            status_code=422
        )


class MetadataFetchException(TubeAssistException):
    def __init__(self):
        super().__init__(
            message="Could not fetch video metadata. Check if the video exists and is public.",
            status_code=422
        )


class EmptyTranscriptException(TubeAssistException):
    def __init__(self):
        super().__init__(
            message="Transcript was empty — could not create chunks.",
            status_code=422
        )


class VideoAlreadyIndexedException(TubeAssistException):
    def __init__(self, video_id: str, video_title: str, video_author: str):
        self.video_id = video_id
        self.video_title = video_title
        self.video_author = video_author
        super().__init__(
            message=f"'{video_title}' is already indexed.",
            status_code=409
        )


class VectorStoreException(TubeAssistException):
    def __init__(self, message: str = "Vector store operation failed."):
        super().__init__(
            message=message,
            status_code=500
        )


class RAGException(TubeAssistException):
    def __init__(self, message: str = "Failed to generate answer."):
        super().__init__(
            message=message,
            status_code=500
        )


# ── Handlers ───────────────────────────────────────────────────────────────────
async def tubeassist_exception_handler(request: Request, exc: TubeAssistException) -> JSONResponse:
    if isinstance(exc, VideoAlreadyIndexedException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "video_id": exc.video_id,
                "video_title": exc.video_title,
                "video_author": exc.video_author,
            }
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred."}
    )