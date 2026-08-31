from fastapi import APIRouter, HTTPException
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import json
from app.video.clip_analyzer import ClipAnalyzer

router = APIRouter(prefix="/api/analysis/clips", tags=["analysis"])
analyzer = ClipAnalyzer()


class ClipAnalysisRequest(BaseModel):
    caption_segments: bool = True
    segment_interval: float = 2.0
    clip_embeddings: bool = True
    clip_order_file: Optional[str] = None


@router.post("/{project_path:path}")
async def analyze_clips(project_path: str, data: ClipAnalysisRequest = ClipAnalysisRequest()):
    project_dir = Path(project_path)
    clips_dir = project_dir / "clips"
    analysis_dir = project_dir / "analysis"

    if not clips_dir.exists():
        raise HTTPException(status_code=404, detail="Clips directory not found")

    analysis_dir.mkdir(exist_ok=True)

    ordered_filenames = None
    order_file_path = None

    if data.clip_order_file:
        order_file_path = Path(data.clip_order_file)
    else:
        default_order = analysis_dir / "clip_order.json"
        if default_order.exists():
            order_file_path = default_order

    if order_file_path and order_file_path.exists():
        with open(order_file_path, "r") as f:
            order_data = json.load(f)
        ordered_filenames = [c["filename"] for c in order_data.get("clips", [])]

    try:
        clips = analyzer.analyze_all_clips(
            str(clips_dir),
            caption_segments=data.caption_segments,
            segment_interval=data.segment_interval,
            clip_embeddings=data.clip_embeddings,
            ordered_filenames=ordered_filenames,
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
