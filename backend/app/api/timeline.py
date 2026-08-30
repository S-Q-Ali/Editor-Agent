from fastapi import APIRouter, HTTPException
from pathlib import Path
import json
from app.agents.editor_brain import EditingBrain

router = APIRouter(prefix="/api/timeline", tags=["timeline"])
brain = EditingBrain()


@router.post("/{project_path:path}/generate")
async def generate_timeline(project_path: str):
    project_dir = Path(project_path)
    analysis_dir = project_dir / "analysis"
    timeline_dir = project_dir / "timeline"

    music_file = analysis_dir / "music_analysis.json"
    lyrics_file = analysis_dir / "lyrics_alignment.json"
    clips_file = analysis_dir / "clip_embeddings.json"
    search_file = analysis_dir / "clip_embeddings.json"

    if not music_file.exists():
        raise HTTPException(status_code=404, detail="Music analysis not found")
    if not lyrics_file.exists():
        raise HTTPException(status_code=404, detail="Lyrics alignment not found")
    if not clips_file.exists():
        raise HTTPException(status_code=404, detail="Clip analysis not found")

    with open(music_file, "r") as f:
        music_analysis = json.load(f)
    with open(lyrics_file, "r") as f:
        lyrics_alignment = json.load(f)
    with open(clips_file, "r") as f:
        clips_data = json.load(f)

    clips = clips_data.get("clips", [])

    lyrics_matches = {}
    segment_matches = {}
    if search_file.exists():
        with open(search_file, "r") as f:
            embeddings_data = json.load(f)
        from app.embeddings.semantic_search import SemanticSearch
        search_engine = SemanticSearch()
        enriched_clips = embeddings_data.get("clips", [])
        lyrics_matches = search_engine.search_for_lyrics(
            lyrics_alignment.get("lines", []),
            enriched_clips
        )
        segment_matches = search_engine.search_segments_for_lyrics(
            lyrics_alignment.get("lines", []),
            enriched_clips
        )

    timeline = brain.generate_timeline(
        music_analysis, lyrics_alignment, clips, lyrics_matches, segment_matches
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


@router.post("/{project_path:path}/validate")
async def validate_timeline(project_path: str):
    timeline_file = Path(project_path) / "timeline" / "timeline.json"
    if not timeline_file.exists():
        raise HTTPException(status_code=404, detail="Timeline not found")

    with open(timeline_file, "r") as f:
        timeline = json.load(f)

    validation = brain.validate_timeline(timeline)
    return validation
