from fastapi import APIRouter, HTTPException
from pathlib import Path
from pydantic import BaseModel
import json
from app.video.clip_analyzer import ClipAnalyzer

router = APIRouter(prefix="/api/analysis/clips", tags=["analysis"])
analyzer = ClipAnalyzer()


class ClipAnalysisRequest(BaseModel):
    caption_segments: bool = True
    segment_interval: float = 2.0


@router.post("/{project_path:path}")
async def analyze_clips(project_path: str, data: ClipAnalysisRequest = ClipAnalysisRequest()):
    project_dir = Path(project_path)
    clips_dir = project_dir / "clips"
    analysis_dir = project_dir / "analysis"

    if not clips_dir.exists():
        raise HTTPException(status_code=404, detail="Clips directory not found")

    analysis_dir.mkdir(exist_ok=True)

    try:
        clips = analyzer.analyze_all_clips(
            str(clips_dir),
            caption_segments=data.caption_segments,
            segment_interval=data.segment_interval,
        )
        analyzer.save_clip_index(clips, str(analysis_dir / "clip_index.json"))

        return {
            "total_clips": len(clips),
            "clips": clips,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_path:path}")
async def get_clip_index(project_path: str):
    index_file = Path(project_path) / "analysis" / "clip_index.json"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Clip index not found")

    with open(index_file, "r") as f:
        return json.load(f)
