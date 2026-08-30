from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.qc.checker import QualityChecker

router = APIRouter(prefix="/api/qc", tags=["qc"])
checker = QualityChecker()


@router.post("/{project_path:path}")
async def run_qc(project_path: str):
    results = checker.run_full_qc(project_path)
    return results


@router.post("/{project_path:path}/timeline")
async def check_timeline(project_path: str):
    timeline_file = Path(project_path) / "timeline" / "timeline.json"
    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    import json
    with open(timeline_file, "r") as f:
        timeline = json.load(f)

    return checker.check_timeline(timeline)


@router.post("/{project_path:path}/render")
async def check_render(project_path: str):
    renders_dir = Path(project_path) / "renders"
    preview_file = renders_dir / "preview.mp4"
    final_file = renders_dir / "final.mp4"

    video_path = None
    if final_file.exists():
        video_path = str(final_file)
    elif preview_file.exists():
        video_path = str(preview_file)

    if not video_path:
        raise HTTPException(status_code=404, detail="No render found")

    return checker.check_render(video_path)
