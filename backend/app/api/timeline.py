from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import json
from app.agents.editor_brain import EditingBrain

router = APIRouter(prefix="/api/timeline", tags=["timeline"])
brain = EditingBrain()


class TimelineGenerateRequest(BaseModel):
    mode: str = "auto"


class EventPatch(BaseModel):
    source_start: Optional[float] = None
    source_end: Optional[float] = None
    clip_id: Optional[str] = None


@router.post("/{project_path:path}/generate")
async def generate_timeline(project_path: str, data: TimelineGenerateRequest = TimelineGenerateRequest()):
    project_dir = Path(project_path)
    analysis_dir = project_dir / "analysis"
    timeline_dir = project_dir / "timeline"

    music_file = analysis_dir / "music_analysis.json"
    lyrics_file = analysis_dir / "lyrics_alignment.json"
    clips_file = analysis_dir / "clip_embeddings.json"

    if not music_file.exists():
        raise HTTPException(status_code=404, detail="Music analysis not found")
    if not clips_file.exists():
        raise HTTPException(status_code=404, detail="Clip analysis not found")

    with open(music_file, "r") as f:
        music_analysis = json.load(f)

    if lyrics_file.exists():
        with open(lyrics_file, "r") as f:
            lyrics_alignment = json.load(f)
    else:
        lyrics_alignment = {"lines": [], "total_lines": 0}

    with open(clips_file, "r") as f:
        clips_data = json.load(f)

    clips = clips_data.get("clips", [])

    lyrics_matches = {}
    segment_matches = {}
    clip_level_matches = {}
    clips_dir = project_dir / "clips"
    video_dir = str(clips_dir) if clips_dir.exists() else ""
    if clips_file.exists():
        with open(clips_file, "r") as f:
            embeddings_data = json.load(f)
        from app.embeddings.semantic_search import SemanticSearch
        search_engine = SemanticSearch()
        enriched_clips = embeddings_data.get("clips", [])

        clip_level_matches = search_engine.search_clips_for_lyrics(
            lyrics_alignment.get("lines", []),
            enriched_clips,
        )

        segment_matches = search_engine.search_segments_for_lyrics(
            lyrics_alignment.get("lines", []),
            enriched_clips,
            video_dir=video_dir,
        )

        lyrics_matches = search_engine.search_for_lyrics(
            lyrics_alignment.get("lines", []),
            enriched_clips,
        )

    clip_order = None
    if data.mode == "sequential":
        order_file = analysis_dir / "clip_order.json"
        if order_file.exists():
            with open(order_file, "r") as f:
                clip_order = json.load(f).get("clips", [])
        else:
            data.mode = "auto"

    timeline = brain.generate_timeline(
        music_analysis, lyrics_alignment, clips, lyrics_matches,
        segment_matches, clip_level_matches,
        mode=data.mode, clip_order=clip_order,
    )

    validation = brain.validate_timeline(timeline)
    timeline["validation"] = validation

    timeline_dir.mkdir(exist_ok=True)
    with open(timeline_dir / "timeline.json", "w") as f:
        json.dump(timeline, f, indent=2)

    return timeline


@router.get("/{project_path:path}")
async def get_timeline(project_path: str):
    timeline_file = Path(project_path) / "timeline" / "timeline.json"
    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with open(timeline_file, "r") as f:
        return json.load(f)


@router.patch("/{project_path:path}/events/{event_index:int}")
async def patch_event(project_path: str, event_index: int, patch: EventPatch):
    timeline_file = Path(project_path) / "timeline" / "timeline.json"
    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with open(timeline_file, "r") as f:
        timeline = json.load(f)

    events = timeline.get("tracks", {}).get("video", [])
    if event_index < 0 or event_index >= len(events):
        raise HTTPException(status_code=404, detail=f"Event index {event_index} out of range")

    event = events[event_index]

    if patch.source_start is not None:
        event["source_start"] = round(patch.source_start, 3)
    if patch.source_end is not None:
        event["source_end"] = round(patch.source_end, 3)
    if patch.clip_id is not None:
        event["clip_id"] = patch.clip_id

    event["selection_method"] = "manual_override"

    with open(timeline_file, "w") as f:
        json.dump(timeline, f, indent=2)

    return {"status": "ok", "event": event}


@router.post("/{project_path:path}/validate")
async def validate_timeline(project_path: str):
    timeline_file = Path(project_path) / "timeline" / "timeline.json"
    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with open(timeline_file, "r") as f:
        timeline = json.load(f)

    validation = brain.validate_timeline(timeline)
    return validation
