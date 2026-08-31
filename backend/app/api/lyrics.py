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


@router.post("/{project_path:path}/auto")
async def auto_extract_lyrics(project_path: str):
    project_dir = Path(project_path)
    lyrics_dir = project_dir / "lyrics"
    analysis_dir = project_dir / "analysis"
    music_dir = project_dir / "music"

    lyrics_dir.mkdir(exist_ok=True)
    analysis_dir.mkdir(exist_ok=True)

    audio_files = (
        list(music_dir.glob("*.mp3"))
        + list(music_dir.glob("*.wav"))
        + list(music_dir.glob("*.flac"))
        + list(music_dir.glob("*.ogg"))
        + list(music_dir.glob("*.m4a"))
    )

    if not audio_files:
        raise HTTPException(status_code=404, detail="No audio file found in music/ directory")

    audio_path = str(audio_files[0])

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_path, word_timestamps=True)

        words_list = []
        text_lines = []
        current_line = {"text": "", "start": None, "end": None}

        for segment in segments:
            for word_info in segment.words:
                words_list.append({
                    "word": word_info.word,
                    "start": word_info.start,
                    "end": word_info.end,
                })

                word_text = word_info.word.strip()
                if not word_text:
                    continue

                if current_line["start"] is None:
                    current_line["start"] = word_info.start

                current_line["text"] += word_info.word
                current_line["end"] = word_info.end

                if word_info.word.strip().endswith((".", "!", "?", ",", ";", ":")) or len(current_line["text"].split()) >= 8:
                    text_lines.append(current_line)
                    current_line = {"text": "", "start": None, "end": None}

        if current_line["text"].strip():
            text_lines.append(current_line)

        lyrics_text = "\n".join(line["text"].strip() for line in text_lines)
        with open(lyrics_dir / "lyrics.txt", "w") as f:
            f.write(lyrics_text)

        alignment = []
        for line in text_lines:
            text = line["text"].strip()
            if text:
                alignment.append({
                    "text": text,
                    "section": "Auto-detected",
                    "timestamp": line["start"],
                    "start": line["start"],
                    "end": line["end"],
                    "importance": engine._estimate_importance(text),
                })

        engine.save_alignment(alignment, str(analysis_dir / "lyrics_alignment.json"))

        return {
            "source": "whisper_auto",
            "total_lines": len(alignment),
            "lines": alignment,
            "language": info.language,
            "duration": info.duration,
        }

    except ImportError:
        raise HTTPException(status_code=500, detail="faster-whisper not installed. Cannot auto-transcribe.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Whisper transcription failed: {str(e)}")


@router.get("/{project_path:path}")
async def get_lyrics_alignment(project_path: str):
    alignment_file = Path(project_path) / "analysis" / "lyrics_alignment.json"
    if not alignment_file.exists():
        raise HTTPException(status_code=404, detail="Lyrics alignment not found")

    with open(alignment_file, "r") as f:
        return json.load(f)
