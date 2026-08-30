from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import os

router = APIRouter(prefix="/api/upload", tags=["upload"])


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

    return {"clips": uploaded, "count": len(uploaded)}
