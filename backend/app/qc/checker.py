import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


class QualityChecker:
    def __init__(self):
        self.checks = []

    def run_full_qc(self, project_path: str) -> Dict[str, Any]:
        project_dir = Path(project_path)
        timeline_file = project_dir / "timeline" / "timeline.json"
        renders_dir = project_dir / "renders"

        results = {
            "score": 100,
            "warnings": [],
            "errors": [],
            "checks": [],
        }

        if timeline_file.exists():
            with open(timeline_file, "r") as f:
                timeline = json.load(f)
            self._check_timeline(timeline, results)

        preview_file = renders_dir / "preview.mp4"
        if preview_file.exists():
            self._check_render(str(preview_file), results)

        final_file = renders_dir / "final.mp4"
        if final_file.exists():
            self._check_render(str(final_file), results)

        results["score"] = max(0, 100 - len(results["errors"]) * 10 - len(results["warnings"]) * 2)

        return results

    def check_timeline(self, timeline: Dict) -> Dict[str, Any]:
        results = {
            "score": 100,
            "warnings": [],
            "errors": [],
            "checks": [],
        }
        self._check_timeline(timeline, results)
        results["score"] = max(0, 100 - len(results["errors"]) * 10 - len(results["warnings"]) * 2)
        return results

    def check_render(self, video_path: str) -> Dict[str, Any]:
        results = {
            "score": 100,
            "warnings": [],
            "errors": [],
            "checks": [],
        }
        self._check_render(video_path, results)
        results["score"] = max(0, 100 - len(results["errors"]) * 10 - len(results["warnings"]) * 2)
        return results

    def _check_timeline(self, timeline: Dict, results: Dict):
        events = timeline.get("tracks", {}).get("video", [])
        duration = timeline.get("duration", 0)

        self._check_duration(events, duration, results)
        self._check_gaps(events, results)
        self._check_overlaps(events, results)
        self._check_timestamps(events, results)
        self._check_confidence(events, results)
        self._check_repetition(events, results)

    def _check_duration(self, events: List[Dict], expected_duration: float, results: Dict):
        if not events:
            results["warnings"].append("No events in timeline")
            results["checks"].append({"name": "duration", "passed": False})
            return

        actual_start = events[0]["timeline_start"]
        actual_end = events[-1]["timeline_end"]

        if actual_start > 0.5:
            results["warnings"].append(f"Timeline doesn't start at 0 (starts at {actual_start:.2f}s)")

        if expected_duration > 0 and actual_end < expected_duration - 1.0:
            results["warnings"].append(f"Timeline is shorter than audio ({actual_end:.2f}s vs {expected_duration:.2f}s)")

        results["checks"].append({"name": "duration", "passed": True})

    def _check_gaps(self, events: List[Dict], results: Dict):
        for i in range(len(events) - 1):
            gap = events[i+1]["timeline_start"] - events[i]["timeline_end"]
            if gap > 0.5:
                results["warnings"].append(f"Gap of {gap:.2f}s between events {i} and {i+1}")

        results["checks"].append({"name": "gaps", "passed": True})

    def _check_overlaps(self, events: List[Dict], results: Dict):
        for i in range(len(events) - 1):
            if events[i]["timeline_end"] > events[i+1]["timeline_start"] + 0.1:
                overlap = events[i]["timeline_end"] - events[i+1]["timeline_start"]
                results["errors"].append(f"Overlap of {overlap:.2f}s between events {i} and {i+1}")

        results["checks"].append({"name": "overlaps", "passed": True})

    def _check_timestamps(self, events: List[Dict], results: Dict):
        for i, event in enumerate(events):
            if event["timeline_start"] >= event["timeline_end"]:
                results["errors"].append(f"Event {i}: start >= end")
            if event["source_start"] >= event["source_end"]:
                results["errors"].append(f"Event {i}: source start >= source end")
            if event["timeline_start"] < 0:
                results["errors"].append(f"Event {i}: negative timeline start")

        results["checks"].append({"name": "timestamps", "passed": True})

    def _check_confidence(self, events: List[Dict], results: Dict):
        low_confidence = [e for e in events if e.get("confidence", 0) < 0.3]
        if low_confidence:
            results["warnings"].append(f"{len(low_confidence)} events with low confidence (<0.3)")

        results["checks"].append({"name": "confidence", "passed": True})

    def _check_repetition(self, events: List[Dict], results: Dict):
        clip_counts = {}
        for event in events:
            clip_id = event["clip_id"]
            clip_counts[clip_id] = clip_counts.get(clip_id, 0) + 1

        repeated = {k: v for k, v in clip_counts.items() if v > 3}
        if repeated:
            results["warnings"].append(f"High repetition: {repeated}")

        results["checks"].append({"name": "repetition", "passed": True})

    def _check_render(self, video_path: str, results: Dict):
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            video_path,
        ]

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                results["errors"].append("Failed to probe render file")
                results["checks"].append({"name": "render_probe", "passed": False})
                return

            data = json.loads(proc.stdout)

            video_stream = None
            audio_stream = None
            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                elif stream.get("codec_type") == "audio":
                    audio_stream = stream

            if video_stream:
                width = int(video_stream.get("width", 0))
                height = int(video_stream.get("height", 0))
                if width < 1920 or height < 1080:
                    results["warnings"].append(f"Resolution below 1080p: {width}x{height}")
            else:
                results["errors"].append("No video stream found in render")

            if not audio_stream:
                results["errors"].append("No audio stream found in render")
            else:
                sample_rate = int(audio_stream.get("sample_rate", 0))
                if sample_rate < 44100:
                    results["warnings"].append(f"Low audio sample rate: {sample_rate}Hz")

            results["checks"].append({"name": "render_quality", "passed": True})

        except Exception as e:
            results["errors"].append(f"Render check failed: {str(e)}")
            results["checks"].append({"name": "render_quality", "passed": False})
