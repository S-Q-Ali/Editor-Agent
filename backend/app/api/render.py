from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import json
from app.rendering.ffmpeg_renderer import FFmpegRenderer
from app.rendering.caption_templates import get_available_templates

router = APIRouter(prefix="/api/render", tags=["rendering"])
renderer = FFmpegRenderer()


class RenderRequest(BaseModel):
    preview: bool = True
    caption_template: str = "none"
    caption_fontsize: Optional[int] = None
    caption_fontcolor: Optional[str] = None


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
                  list(music_dir.glob("*.flac")) + list(music_dir.glob("*.ogg"))

    if not audio_files:
        raise HTTPException(status_code=404, detail="Audio file not found")

    renders_dir.mkdir(exist_ok=True)

    if data.preview:
        output_file = renders_dir / "preview.mp4"
    else:
        output_file = renders_dir / "final.mp4"

    result = renderer.render(
        timeline=timeline,
        clips_dir=str(clips_dir),
        audio_path=str(audio_files[0]),
        output_path=str(output_file),
        preview=data.preview,
        caption_template=data.caption_template,
        caption_fontsize=data.caption_fontsize,
        caption_fontcolor=data.caption_fontcolor,
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    from app.storage.project_manager import ProjectManager
    updates = {"preview_ready": True, "status": "preview_ready"} if data.preview \
        else {"status": "final_rendered"}
    ProjectManager().update_project(project_path, updates)

    return result


@router.get("/{project_path:path}/status")
async def get_render_status(project_path: str):
    renders_dir = Path(project_path) / "renders"
    if not renders_dir.exists():
        return {"renders": []}

    renders = []
    for f in renders_dir.glob("*.mp4"):
        renders.append({
            "filename": f.name,
            "path": str(f),
            "size": f.stat().st_size,
        })

    return {"renders": renders}


@router.get("/{project_path:path}/download")
async def download_render(project_path: str):
    renders_dir = Path(project_path) / "renders"
    final_file = renders_dir / "final.mp4"

    if not final_file.exists():
        preview_file = renders_dir / "preview.mp4"
        if preview_file.exists():
            return FileResponse(
                path=str(preview_file),
                filename="preview.mp4",
                media_type="video/mp4",
            )
        raise HTTPException(status_code=404, detail="No rendered video found")

    return FileResponse(
        path=str(final_file),
        filename="final.mp4",
        media_type="video/mp4",
    )


@router.get("/captions/templates")
async def list_caption_templates():
    return {"templates": get_available_templates()}
