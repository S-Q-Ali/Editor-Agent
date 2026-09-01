from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json
from app.rendering.ffmpeg_renderer import FFmpegRenderer
from app.rendering.caption_templates import get_available_templates
from app.utils.progress import update_progress, complete_step, fail_step

router = APIRouter(prefix="/api/render", tags=["rendering"])
renderer = FFmpegRenderer()


class RenderRequest(BaseModel):
    preview: bool = True
    caption_template: str = "none"
    caption_fontsize: Optional[int] = None
    caption_fontcolor: Optional[str] = None
    resolution: str = "1080p"
    crf: int = 23
    preset: str = "medium"
    codec: str = "h264"
    fps: int = 30
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    audio_sample_rate: int = 48000
    audio_channels: int = 2
    container: str = "mp4"
    export_path: Optional[str] = None


class EstimateRequest(BaseModel):
    crf: int = 23
    resolution: str = "1080p"
    audio_bitrate: str = "192k"
    audio_codec: str = "aac"


@router.get("/captions/templates")
async def list_caption_templates():
    return {"templates": get_available_templates()}


@router.post("/{project_path:path}/estimate")
async def estimate_file_size(project_path: str, data: EstimateRequest):
    project_dir = Path(project_path)
    timeline_file = project_dir / "timeline" / "timeline.json"

    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with open(timeline_file, "r") as f:
        timeline = json.load(f)

    duration = timeline.get("duration", 0)

    estimate = FFmpegRenderer.estimate_file_size(
        duration=duration,
        crf=data.crf,
        resolution=data.resolution,
        audio_bitrate=data.audio_bitrate,
        audio_codec=data.audio_codec,
    )

    return {
        "duration": duration,
        **estimate,
    }


@router.get("/{project_path:path}/status")
async def get_render_status(project_path: str):
    renders_dir = Path(project_path) / "renders"
    if not renders_dir.exists():
        return {"renders": []}

    renders = []
    for f in renders_dir.glob("*.*"):
        if f.suffix in (".mp4", ".webm", ".mkv", ".avi"):
            renders.append({
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
            })

    return {"renders": renders}


@router.get("/{project_path:path}/download")
async def download_render(project_path: str):
    renders_dir = Path(project_path) / "renders"
    if not renders_dir.exists():
        raise HTTPException(status_code=404, detail="No rendered video found")

    final_candidates = list(renders_dir.glob("final.*"))
    if final_candidates:
        final_file = final_candidates[0]
        return FileResponse(
            path=str(final_file),
            filename=final_file.name,
            media_type="video/mp4",
        )

    preview_file = renders_dir / "preview.mp4"
    if preview_file.exists():
        return FileResponse(
            path=str(preview_file),
            filename="preview.mp4",
            media_type="video/mp4",
        )

    raise HTTPException(status_code=404, detail="No rendered video found")


@router.post("/{project_path:path}")
async def render_video(project_path: str, data: RenderRequest):
    project_dir = Path(project_path)
    timeline_file = project_dir / "timeline" / "timeline.json"
    music_dir = project_dir / "music"
    clips_dir = project_dir / "clips"
    renders_dir = project_dir / "renders"

    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with open(timeline_file, "r") as f:
        timeline = json.load(f)

    audio_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav")) + \
                  list(music_dir.glob("*.flac")) + list(music_dir.glob("*.ogg")) + \
                  list(music_dir.glob("*.m4a"))

    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio file not found")

    renders_dir.mkdir(exist_ok=True)

    update_progress(project_path, "rendering_preview", 10, "Preparing render...")

    if data.export_path:
        output_file = Path(data.export_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    elif data.preview:
        output_file = renders_dir / "preview.mp4"
    else:
        output_file = renders_dir / f"final.{data.container}"

    update_progress(project_path, "rendering_preview", 30, "Rendering video with FFmpeg...")
    result = renderer.render(
        timeline=timeline,
        clips_dir=str(clips_dir),
        audio_path=str(audio_files[0]),
        output_path=str(output_file),
        preview=data.preview,
        caption_template=data.caption_template,
        caption_fontsize=data.caption_fontsize,
        caption_fontcolor=data.caption_fontcolor,
        resolution=data.resolution,
        crf=data.crf,
        preset=data.preset,
        codec=data.codec,
        fps=data.fps,
        audio_codec=data.audio_codec,
        audio_bitrate=data.audio_bitrate,
        audio_sample_rate=data.audio_sample_rate,
        audio_channels=data.audio_channels,
        container=data.container,
    )

    if result.get("error"):
        fail_step(project_path, "rendering_preview", result["error"])
        raise HTTPException(status_code=500, detail=result["error"])

    update_progress(project_path, "rendering_preview", 95, "Finalizing...")
    from app.storage.project_manager import ProjectManager
    updates = {"preview_ready": True, "status": "preview_ready"} if data.preview \
        else {"status": "final_rendered"}
    ProjectManager().update_project(project_path, updates)

    complete_step(project_path, "rendering_preview")
    return result
