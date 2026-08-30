from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{project_path:path}/{file_path:path}")
async def serve_file(project_path: str, file_path: str):
    full_path = Path(project_path) / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path))
