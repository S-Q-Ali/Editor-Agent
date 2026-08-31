from fastapi import APIRouter, HTTPException
from pathlib import Path
from app.audio.analyzer import MusicAnalyzer

router = APIRouter(prefix="/api/analysis/music", tags=["analysis"])
analyzer = MusicAnalyzer()


@router.post("/{project_path:path}")
async def analyze_music(project_path: str):
    project_dir = Path(project_path)
    music_dir = project_dir / "music"

    if not music_dir.exists():
        raise HTTPException(status_code=404, detail="Music directory not found")

    audio_files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav")) + \
                  list(music_dir.glob("*.flac")) + list(music_dir.glob("*.ogg")) + \
                  list(music_dir.glob("*.m4a"))

    if not audio_files:
        raise HTTPException(status_code=404, detail="No audio files found")

    audio_path = str(audio_files[0])

    try:
        result = analyzer.analyze(audio_path)

        analysis_dir = project_dir / "analysis"
        analysis_dir.mkdir(exist_ok=True)

        import json
        with open(analysis_dir / "music_analysis.json", "w") as f:
            json.dump(result, f, indent=2)

        from app.storage.project_manager import ProjectManager
        ProjectManager().update_project(project_path, {"music_file": audio_files[0].name})

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_path:path}")
async def get_music_analysis(project_path: str):
    analysis_file = Path(project_path) / "analysis" / "music_analysis.json"
    if not analysis_file.exists():
        raise HTTPException(status_code=404, detail="Analysis not found")

    import json
    with open(analysis_file, "r") as f:
        return json.load(f)
