from fastapi import APIRouter
import shutil

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health_check():
    ffmpeg_available = shutil.which("ffmpeg") is not None
    ffprobe_available = shutil.which("ffprobe") is not None

    return {
        "status": "healthy",
        "ffmpeg": ffmpeg_available,
        "ffprobe": ffprobe_available,
    }
