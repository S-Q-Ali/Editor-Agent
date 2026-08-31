from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json
import shutil
import os
from app.storage.project_manager import ProjectManager

router = APIRouter(prefix="/api/upload", tags=["upload"])


class ClipOrderItem(BaseModel):
    index: int
    filename: str


class ClipOrderRequest(BaseModel):
    mode: str = "sequential"
    clips: List[ClipOrderItem]


@router.post("/music/{project_path:path}")
async def upload_music(project_path: str, file: UploadFile = File(...)):
    project_dir = Path(project_path)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    music_dir = project_dir / "music"
    music_dir.mkdir(exist_ok=True)

    file_path = music_dir / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": file.filename, "path": str(file_path), "size": file_path.stat().st_size}


@router.post("/lyrics/{project_path:path}")
async def upload_lyrics(project_path: str, file: UploadFile = File(...)):
    project_dir = Path(project_path)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    lyrics_dir = project_dir / "lyrics"
    lyrics_dir.mkdir(exist_ok=True)

    file_path = lyrics_dir / file.filename
    content = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content)

    return {"filename": file.filename, "path": str(file_path), "size": len(content)}


@router.post("/clips/{project_path:path}")
async def upload_clips(project_path: str, files: list[UploadFile] = File(...)):
    project_dir = Path(project_path)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    clips_dir = project_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    uploaded = []
    for file in files:
        file_path = clips_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded.append({"filename": file.filename, "path": str(file_path), "size": file_path.stat().st_size})

    pm = ProjectManager()
    existing_clips = []
    project_data = pm.get_project(project_path)
    if project_data:
        existing_clips = project_data.get("clips", [])

    existing_filenames = {c.get("filename") for c in existing_clips}
    for item in uploaded:
        if item["filename"] not in existing_filenames:
            stem = Path(item["filename"]).stem
            existing_clips.append({"clip_id": stem, "filename": item["filename"]})

    pm.update_project(project_path, {"clips": existing_clips})

    return {"clips": uploaded, "count": len(uploaded)}


@router.post("/clips/{project_path:path}/order")
async def save_clip_order(project_path: str, request: ClipOrderRequest):
    project_dir = Path(project_path)
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    analysis_dir = project_dir / "analysis"
    analysis_dir.mkdir(exist_ok=True)

    clip_order = {
        "mode": request.mode,
        "clips": [{"index": c.index, "filename": c.filename} for c in request.clips],
    }

    order_file = analysis_dir / "clip_order.json"
    with open(order_file, "w") as f:
        json.dump(clip_order, f, indent=2)

    return {"status": "ok", "clip_order_file": str(order_file), "clip_count": len(request.clips)}
