import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import random


@dataclass
class TimelineEvent:
    clip_id: str
    source_start: float
    source_end: float
    timeline_start: float
    timeline_end: float
    transition: str
    reason: str
    confidence: float
    lyric_text: str = ""


class EditingBrain:
    def __init__(self):
        self.transitions = ["cut", "fade", "crossfade", "dissolve"]
        self.max_repetition = 2

    def generate_timeline(
        self,
        music_analysis: Dict,
        lyrics_alignment: Dict,
        clips: List[Dict],
        lyrics_matches: Dict,
        segment_matches: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        duration = music_analysis.get("duration", 0)
        beats = music_analysis.get("beats", [])
        sections = music_analysis.get("sections", [])
        lyrics_lines = lyrics_alignment.get("lines", [])

        if not lyrics_lines:
            return self._generate_empty_timeline(duration)

        timeline_events = []
        used_clips = {}
        current_time = 0

        for line in lyrics_lines:
            if current_time >= duration:
                break

            line_start = line.get("start", current_time)
            line_end = line.get("end", line_start + 2.0)
            line_duration = line_end - line_start

            if line_duration <= 0:
                line_duration = 2.0

            clip_result = None
            if segment_matches:
                clip_result = self._select_clip_with_segment(
                    line, clips, segment_matches, used_clips, line_duration
                )

            if not clip_result:
                clip_result = self._select_clip(
                    line, clips, lyrics_matches, used_clips, line_duration
                )

            if not clip_result and clips:
                fallback_clip = clips[0]
                clip_result = (
                    fallback_clip, 0, min(line_duration, fallback_clip.get("duration", line_duration)),
                    0.1, "No suitable clip found, using fallback"
                )

            if clip_result:
                clip, source_start, source_end, confidence, reason = clip_result

                source_start = self._snap_to_beats(source_start, beats)

                event = TimelineEvent(
                    clip_id=clip.get("clip_id", "unknown"),
                    source_start=source_start,
                    source_end=source_end,
                    timeline_start=current_time,
                    timeline_end=current_time + line_duration,
                    transition=self._select_transition(current_time, sections),
                    reason=reason,
                    confidence=confidence,
                    lyric_text=line.get("text", ""),
                )
                timeline_events.append(asdict(event))

                clip_id = clip.get("clip_id", "unknown")
                used_clips[clip_id] = used_clips.get(clip_id, 0) + 1

            current_time += line_duration

        timeline = {
            "version": 1,
            "duration": duration,
            "total_events": len(timeline_events),
            "tracks": {
                "video": timeline_events,
                "audio": [],
            },
            "metadata": {
                "bpm": music_analysis.get("bpm", 0),
                "sections_count": len(sections),
                "lyrics_lines": len(lyrics_lines),
                "clips_used": len(used_clips),
            },
        }

        return timeline

    def _select_clip(
        self,
        lyric_line: Dict,
        clips: List[Dict],
        lyrics_matches: Dict,
        used_clips: Dict,
        required_duration: float,
    ) -> Optional[tuple]:
        if not clips:
            return None

        lyric_text = lyric_line.get("text", "")
        candidates = []

        match_results = lyrics_matches.get(lyric_text, [])
        if match_results:
            for match in match_results[:3]:
                clip_id = match.clip_id if hasattr(match, 'clip_id') else match.get("clip_id", "")
                score = match.score if hasattr(match, 'score') else match.get("score", 0)
                if score > 0:
                    for clip in clips:
                        if clip.get("clip_id") == clip_id:
                            candidates.append((clip, score))
                            break

        if not candidates:
            for clip in clips:
                clip_id = clip.get("clip_id", "unknown")
                times_used = used_clips.get(clip_id, 0)
                if times_used < self.max_repetition:
                    quality = clip.get("quality_score", 0.5)
                    candidates.append((clip, quality))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)

        for clip, base_score in candidates:
            clip_id = clip.get("clip_id", "unknown")
            times_used = used_clips.get(clip_id, 0)

            clip_duration = clip.get("duration", 0)
            best_segments = clip.get("best_segments", [])

            repetition_penalty = max(0.1, 1.0 - times_used * 0.15)

            if best_segments:
                for seg in best_segments:
                    seg_duration = seg["end"] - seg["start"]
                    if seg_duration >= required_duration * 0.8:
                        confidence = base_score * repetition_penalty
                        reason = f"Semantic match (score: {base_score:.2f}), segment quality: {seg['score']:.2f}, used: {times_used}x"
                        return (clip, seg["start"], seg["start"] + required_duration, confidence, reason)

            if clip_duration >= required_duration:
                source_start = 0
                confidence = base_score * 0.8 * repetition_penalty
                reason = f"Best available clip (quality: {base_score:.2f}, used: {times_used}x)"
                return (clip, source_start, source_start + required_duration, confidence, reason)

        clip, base_score = candidates[0]
        clip_id = clip.get("clip_id", "unknown")
        clip_duration = clip.get("duration", 0)
        times_used = used_clips.get(clip_id, 0)
        actual_duration = min(required_duration, clip_duration)
        repetition_penalty = max(0.1, 1.0 - times_used * 0.1)
        confidence = base_score * 0.6 * repetition_penalty
        reason = f"Fallback selection (quality: {base_score:.2f}, used: {times_used}x)"
        return (clip, 0, actual_duration, confidence, reason)

    def _select_clip_with_segment(
        self,
        lyric_line: Dict,
        clips: List[Dict],
        segment_matches: Dict,
        used_clips: Dict,
        required_duration: float,
    ) -> Optional[tuple]:
        """Try to find a specific segment in a clip that matches the lyric."""
        lyric_text = lyric_line.get("text", "")
        matches = segment_matches.get(lyric_text, [])

        for match in matches:
            score = match.get("score", 0)
            if score < 0.2:
                continue

            clip_id = match.get("clip_id", "")
            clip = next((c for c in clips if c.get("clip_id") == clip_id), None)
            if not clip:
                continue

            seg_start = match.get("segment_start", 0)
            seg_end = match.get("segment_end", 0)
            seg_duration = seg_end - seg_start
            if seg_duration < required_duration * 0.3:
                continue

            times_used = used_clips.get(clip_id, 0)
            repetition_penalty = max(0.1, 1.0 - times_used * 0.15)

            actual_end = min(seg_start + required_duration, clip.get("duration", seg_end))
            confidence = score * repetition_penalty
            caption = match.get("caption", "")
            reason = f"Segment match: \"{caption}\" (score: {score:.2f}, used: {times_used}x)"
            return (clip, seg_start, actual_end, confidence, reason)

        return None

    def _snap_to_beats(self, time: float, beats: List[float], tolerance: float = 0.3) -> float:
        """Snap a timestamp to the nearest beat if within tolerance."""
        if not beats:
            return time
        nearest = min(beats, key=lambda b: abs(b - time))
        if abs(nearest - time) <= tolerance:
            return round(nearest, 3)
        return time

    def _select_transition(self, current_time: float, sections: List[Dict]) -> str:
        for section in sections:
            if section["start"] <= current_time <= section["end"]:
                label = section.get("label", "").lower()
                if "chorus" in label:
                    return random.choice(["crossfade", "dissolve"])
                elif "verse" in label:
                    return "cut"
                elif "bridge" in label:
                    return "fade"
                elif "intro" in label or "outro" in label:
                    return "fade"
        return "cut"

    def _generate_empty_timeline(self, duration: float) -> Dict:
        return {
            "version": 1,
            "duration": duration,
            "total_events": 0,
            "tracks": {"video": [], "audio": []},
            "metadata": {},
        }

    def validate_timeline(self, timeline: Dict) -> Dict:
        errors = []
        warnings = []

        events = timeline.get("tracks", {}).get("video", [])
        duration = timeline.get("duration", 0)

        for i, event in enumerate(events):
            if event["timeline_start"] >= event["timeline_end"]:
                errors.append(f"Event {i}: start >= end")

            if event["source_start"] >= event["source_end"]:
                errors.append(f"Event {i}: source start >= source end")

            if event["confidence"] < 0.3:
                warnings.append(f"Event {i}: low confidence ({event['confidence']:.2f})")

        for i in range(len(events) - 1):
            if events[i]["timeline_end"] > events[i+1]["timeline_start"] + 0.1:
                warnings.append(f"Overlap between events {i} and {i+1}")

        if events and events[0]["timeline_start"] > 0.5:
            warnings.append("Timeline doesn't start at 0")

        if events and events[-1]["timeline_end"] < duration - 0.5:
            warnings.append("Timeline doesn't cover full duration")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
