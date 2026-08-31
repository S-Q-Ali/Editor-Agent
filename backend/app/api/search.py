from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json
from typing import List
from app.embeddings.semantic_search import SemanticSearch

router = APIRouter(prefix="/api/search", tags=["search"])
search_engine = SemanticSearch()


class SearchQuery(BaseModel):
    query: str
    top_k: int = 5


@router.post("/{project_path:path}/index")
async def build_index(project_path: str):
    project_dir = Path(project_path)
    analysis_dir = project_dir / "analysis"
    index_file = analysis_dir / "clip_index.json"

    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Clip analysis not found. Run clip analysis first.")

    with open(index_file, "r") as f:
        clip_data = json.load(f)

    clips = clip_data.get("clips", [])
    if not clips:
        raise HTTPException(status_code=400, detail="No clips found to index")

    enhanced_clips = search_engine.generate_clip_embeddings(clips)
    enhanced_clips = search_engine.generate_segment_embeddings(enhanced_clips)
    search_engine.save_embeddings(enhanced_clips, str(analysis_dir / "clip_embeddings.json"))

    return {
        "indexed_clips": len(enhanced_clips),
        "message": "Embeddings generated and saved",
    }


@router.post("/{project_path:path}/query")
async def search_clips(project_path: str, data: SearchQuery):
    analysis_dir = Path(project_path) / "analysis"
    embeddings_file = analysis_dir / "clip_embeddings.json"

    if not embeddings_file.exists():
        raise HTTPException(status_code=404, detail="Embeddings not found. Build index first.")

    clips = search_engine.load_embeddings(str(embeddings_file))
    if not clips:
        raise HTTPException(status_code=400, detail="No clips in index")

    results = search_engine.search_clips(data.query, clips, data.top_k)
    return {
        "query": data.query,
        "results": [
            {"clip_id": r.clip_id, "score": r.score, "reason": r.reason}
            for r in results
        ],
    }


@router.get("/{project_path:path}/lyrics-match")
async def match_lyrics_to_clips(project_path: str):
    analysis_dir = Path(project_path) / "analysis"
    lyrics_file = analysis_dir / "lyrics_alignment.json"
    embeddings_file = analysis_dir / "clip_embeddings.json"

    if not lyrics_file.exists():
        raise HTTPException(status_code=404, detail="Lyrics alignment not found")
    if not embeddings_file.exists():
        raise HTTPException(status_code=404, detail="Clip embeddings not found")

    with open(lyrics_file, "r") as f:
        lyrics_data = json.load(f)
    clips = search_engine.load_embeddings(str(embeddings_file))

    lyrics = lyrics_data.get("lines", [])
    matches = search_engine.search_for_lyrics(lyrics, clips)

    return {
        "matches": {
            query: [
                {"clip_id": r.clip_id, "score": r.score, "reason": r.reason}
                for r in results
            ]
            for query, results in matches.items()
        },
    }
