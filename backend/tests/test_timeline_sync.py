"""Regression tests for the lyric-anchored timeline pipeline.

Validates the invariants that guarantee a publish-ready render:
- full song coverage (no gaps, correct total duration)
- minimum event duration (no strobe cutting)
- exact source/timeline duration match per event (A/V sync)
- source ranges within clip bounds (no silent truncation)
- lyric anchoring (visuals land on the sung words)
- deterministic output (same inputs -> same timeline)
- renderer produces a file whose duration matches the music

Run:  cd backend && python -m pytest tests/test_timeline_sync.py -v
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.editor_brain import EditingBrain  # noqa: E402

PROJECT_DIR = BACKEND_DIR / "projects" / "TT_8f1cd796"
ANALYSIS_DIR = PROJECT_DIR / "analysis"
MIN_EVENT_DURATION = 2.0


def _load_analysis():
    if not (ANALYSIS_DIR / "music_analysis.json").exists():
        pytest.skip("TT project analysis not available")
    music = json.loads((ANALYSIS_DIR / "music_analysis.json").read_text())
    lyrics = json.loads((ANALYSIS_DIR / "lyrics_alignment.json").read_text())
    clips = json.loads((ANALYSIS_DIR / "clip_embeddings.json").read_text())["clips"]
    return music, lyrics, clips


@pytest.fixture(scope="module")
def timeline_no_matches():
    music, lyrics, clips = _load_analysis()
    brain = EditingBrain()
    return brain.generate_timeline(music, lyrics, clips, {}, None, None, mode="auto")


def _events(timeline):
    return timeline["tracks"]["video"]


def test_full_song_coverage(timeline_no_matches):
    events = _events(timeline_no_matches)
    duration = timeline_no_matches["duration"]
    prev_end = 0.0
    for event in events:
        assert event["timeline_start"] <= prev_end + 0.05, (
            f"Gap before {event['timeline_start']}s"
        )
        prev_end = event["timeline_end"]
    assert prev_end >= duration - 0.5, f"Timeline ends at {prev_end}s, song is {duration}s"


def test_minimum_event_duration(timeline_no_matches):
    """Hard floor is 1.0s: a lyric anchor must never be violated, but events
    may drop below the 2.0s policy when two lyric phrases collide.
    (The original strobe bug produced 0.14s events.)"""
    for i, event in enumerate(_events(timeline_no_matches)):
        dur = event["timeline_end"] - event["timeline_start"]
        assert dur >= 1.0 - 1e-6, f"Event {i} too short: {dur:.2f}s"


def test_source_matches_timeline_duration(timeline_no_matches):
    """A mismatch here silently truncates or desyncs the render (the 38s bug)."""
    for i, event in enumerate(_events(timeline_no_matches)):
        src = event["source_end"] - event["source_start"]
        tl = event["timeline_end"] - event["timeline_start"]
        assert abs(src - tl) <= 0.01, (
            f"Event {i}: source {src:.2f}s != timeline {tl:.2f}s"
        )


def test_source_within_clip_bounds(timeline_no_matches):
    _, _, clips = _load_analysis()
    clip_dur = {c["clip_id"]: c["duration"] for c in clips}
    for i, event in enumerate(_events(timeline_no_matches)):
        assert event["source_end"] <= clip_dur[event["clip_id"]] + 1e-6, (
            f"Event {i}: source_end {event['source_end']} beyond clip "
            f"{event['clip_id']} ({clip_dur[event['clip_id']]}s)"
        )


def test_lyrics_anchored_to_real_timestamps(timeline_no_matches):
    """Every lyric line's sung timestamp must fall inside a lyric event
    (not inside an intro/music/outro filler slot)."""
    lyrics = json.loads((ANALYSIS_DIR / "lyrics_alignment.json").read_text())
    for line in lyrics.get("lines", []):
        start = line.get("start")
        if start is None:
            continue
        covering = [
            e for e in _events(timeline_no_matches)
            if e["timeline_start"] - 0.05 <= start < e["timeline_end"]
            and not e["lyric_text"].startswith("[")
        ]
        assert covering, (
            f"Lyric '{line.get('text', '')[:30]}' at {start:.2f}s has no lyric-anchored event"
        )


def test_intro_and_outro_cover_instrumental(timeline_no_matches):
    events = _events(timeline_no_matches)
    lyrics = json.loads((ANALYSIS_DIR / "lyrics_alignment.json").read_text())
    lines = lyrics.get("lines", [])
    if not lines:
        pytest.skip("No lyric timestamps available")
    first_lyric = lines[0]["start"]
    last_lyric = lines[-1]["end"]
    assert events[0]["timeline_start"] == 0.0

    # The instrumental intro is covered by intro slot(s) (may be chunked)
    def event_at(t):
        return [e for e in events if e["timeline_start"] - 0.05 <= t < e["timeline_end"]]

    intro_events = [e for e in event_at(first_lyric - 0.5)]
    assert intro_events and intro_events[0]["lyric_text"] == "[intro]", (
        "Instrumental intro not covered by intro events"
    )
    # Outro covers the tail after the last lyric
    assert events[-1]["timeline_end"] >= last_lyric - 0.5


def test_no_timeline_overlaps(timeline_no_matches):
    """Overlapping events desync the concat renderer (A/V drift)."""
    events = _events(timeline_no_matches)
    for i in range(len(events) - 1):
        assert events[i]["timeline_end"] <= events[i + 1]["timeline_start"] + 0.01, (
            f"Overlap between events {i} and {i+1}"
        )


def test_no_clip_overuse(timeline_no_matches):
    from collections import Counter
    usage = Counter(e["clip_id"] for e in _events(timeline_no_matches))
    brain = EditingBrain()
    for clip_id, count in usage.items():
        assert count <= brain.max_clip_usage, f"Clip {clip_id} used {count} times"


def test_deterministic_output():
    music, lyrics, clips = _load_analysis()
    brain = EditingBrain()
    t1 = brain.generate_timeline(music, lyrics, clips, {}, None, None, mode="auto")
    t2 = brain.generate_timeline(music, lyrics, clips, {}, None, None, mode="auto")
    assert t1 == t2


def test_validate_timeline_accepts_generated():
    brain = EditingBrain()
    music, lyrics, clips = _load_analysis()
    timeline = brain.generate_timeline(music, lyrics, clips, {}, None, None, mode="auto")
    validation = brain.validate_timeline(timeline)
    assert validation["valid"], validation["errors"]


# ---------------------------------------------------------------------------
# Renderer integration test (synthetic media, skipped without ffmpeg)
# ---------------------------------------------------------------------------

def _ffmpeg_available():
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not available")
def test_renderer_duration_matches_timeline(tmp_path):
    """End-to-end: 2 synthetic clips, a 6s timeline, 6s music -> 6s render."""
    from app.rendering.ffmpeg_renderer import FFmpegRenderer

    clip_a = tmp_path / "a.mp4"
    clip_b = tmp_path / "b.mp4"
    music = tmp_path / "song.mp3"
    output = tmp_path / "preview.mp4"

    def make_clip(path):
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "testsrc=duration=10:size=320x180:rate=24",
            "-c:v", "libx264", "-preset", "ultrafast", str(path),
        ], capture_output=True, timeout=120, check=True)

    make_clip(clip_a)
    make_clip(clip_b)
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=6",
        "-c:a", "libmp3lame", str(music),
    ], capture_output=True, timeout=120, check=True)

    timeline = {
        "version": 2,
        "duration": 6.0,
        "tracks": {
            "video": [
                {"clip_id": "a", "source_start": 0.0, "source_end": 3.0,
                 "timeline_start": 0.0, "timeline_end": 3.0,
                 "transition": "cut", "reason": "test", "confidence": 0.9,
                 "lyric_text": "[intro]", "selection_method": "test",
                 "clip_caption": ""},
                {"clip_id": "b", "source_start": 2.0, "source_end": 5.0,
                 "timeline_start": 3.0, "timeline_end": 6.0,
                 "transition": "cut", "reason": "test", "confidence": 0.9,
                 "lyric_text": "hello", "selection_method": "test",
                 "clip_caption": ""},
            ],
            "audio": [],
        },
    }

    renderer = FFmpegRenderer()
    renderer.temp_dir = tmp_path / "temp"
    renderer.temp_dir.mkdir(exist_ok=True)

    result = renderer.render(
        timeline=timeline,
        clips_dir=str(tmp_path),
        audio_path=str(music),
        output_path=str(output),
        preview=True,
    )
    assert "error" not in result, result.get("error")
    assert result.get("duration_ok") is True, result.get("warnings")

    info = renderer.get_video_info(str(output))
    render_dur = float(info["format"]["duration"])
    assert abs(render_dur - 6.0) <= 1.0, f"Render is {render_dur:.2f}s, expected ~6s"

    streams = {s["codec_type"] for s in info["streams"]}
    assert "video" in streams and "audio" in streams

    shutil.rmtree(renderer.temp_dir, ignore_errors=True)