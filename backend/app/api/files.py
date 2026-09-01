from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/browse")
async def browse_directories(path: str = "C:\\"):
    target = Path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="Not a directory")

    dirs = []
    try:
        for item in sorted(target.iterdir()):
            if item.is_dir() and not item.name.startswith('.'):
                dirs.append({
                    "name": item.name,
                    "path": str(item),
                })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "current": str(target),
        "parent": str(target.parent) if target.parent != target else None,
        "directories": dirs,
    }


@router.get("/{project_path:path}/{file_path:path}")
async def serve_file(project_path: str, file_path: str):
    full_path = Path(project_path) / file_path
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(full_path))
