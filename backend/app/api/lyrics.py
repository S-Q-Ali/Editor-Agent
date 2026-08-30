from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import json
from typing import Optional
from app.lyrics.engine import LyricsEngine

router = APIRouter(prefix="/api/analysis/lyrics", tags=["analysis"])
engine = LyricsEngine()


class LyricsSubmit(BaseModel):
    text: str
    use_whisper: bool = False


@router.post("/{project_path:path}")
async def align_lyrics(project_path: str, data: LyricsSubmit):
    project_dir = Path(project_path)
    lyrics_dir = project_dir / "lyrics"
    analysis_dir = project_dir / "analysis"
    music_dir = project_dir / "music"

    lyrics_dir.mkdir(exist_ok=True)
    analysis_dir.mkdir(exist_ok=True)

    with open(lyrics_dir / "lyrics.txt", "w") as f:
        f.write(data.text)

    music_analysis_file = analysis_dir / "music_analysis.json"
    audio_analysis = {}
    if music_analysis_file.exists():
        with open(music_analysis_file, "r") as f:
            audio_analysis = json.load(f)

    if data.use_whisper:
        audio_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
        if audio_files:
            alignment = engine.align_with_whisper(str(audio_files[0]), data.text)
        else:
            parsed = engine.parse_lyrics(data.text)
            alignment = engine.align_with_audio(parsed, audio_analysis)
    else:
        parsed = engine.parse_lyrics(data.text)
        alignment = engine.align_with_audio(parsed, audio_analysis)

    engine.save_alignment(alignment, str(analysis_dir / "lyrics_alignment.json"))

    return {
        "lines": alignment,
        "total_lines": len(alignment),
    }


@router.get("/{project_path:path}")
async def get_lyrics_alignment(project_path: str):
    alignment_file = Path(project_path) / "analysis" / "lyrics_alignment.json"
    if not alignment_file.exists():
        raise HTTPException(status_code=404, detail="Lyrics alignment not found")

    with open(alignment_file, "r") as f:
        return json.load(f)
