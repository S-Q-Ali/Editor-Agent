import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import random

logger = logging.getLogger(__name__)


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
    selection_method: str = ""


class EditingBrain:
    def __init__(self):
        self.transitions = ["cut", "fade", "crossfade", "dissolve"]
        self.max_repetition = 2
        self.confidence_threshold = 0.15

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
            if beats and len(beats) > 1:
                lyrics_lines = self._generate_beat_grid(beats, duration)
            elif duration > 0:
                lyrics_lines = self._generate_segment_grid(duration)
            else:
                return self._generate_empty_timeline(duration)

        timeline_events = []
        used_clips = {}
        current_time = 0
        prev_clip = None
        prev_source_start = 0
        prev_source_end = 0
        stats = {
            "segment_match_count": 0,
            "semantic_match_count": 0,
            "extend_fallback_count": 0,
            "hard_fallback_count": 0,
            "low_confidence_count": 0,
        }

        for line in lyrics_lines:
            if current_time >= duration:
                break

            line_start = line.get("start", current_time)
            line_end = line.get("end", line_start + 2.0)
            line_duration = line_end - line_start

            if line_duration <= 0:
                line_duration = 2.0

            clip_result = None
            selection_method = ""

            if segment_matches:
                clip_result = self._select_clip_with_segment(
                    line, clips, segment_matches, used_clips, line_duration
                )
                if clip_result:
                    selection_method = "segment_match"
                    stats["segment_match_count"] += 1

            if not clip_result:
                clip_result = self._select_clip(
                    line, clips, lyrics_matches, used_clips, line_duration
                )
                if clip_result:
                    selection_method = "semantic_match"
                    stats["semantic_match_count"] += 1

            if clip_result:
                clip, source_start, source_end, confidence, reason = clip_result
                if confidence < self.confidence_threshold and prev_clip is not None:
                    clip = prev_clip
                    source_start = prev_source_start
                    source_end = prev_source_end
                    confidence = max(0.1, confidence)
                    reason = f"Extended previous clip (low confidence: {confidence:.2f})"
                    selection_method = "extend_fallback"
                    stats["extend_fallback_count"] += 1
                    stats["low_confidence_count"] += 1
                else:
                    source_start = self._snap_to_beats(source_start, beats)
            else:
                if clips:
                    if prev_clip is not None:
                        clip = prev_clip
                        source_start = prev_source_start
                        source_end = prev_source_end
                        confidence = 0.1
                        reason = "Extended previous clip (no match found)"
                        selection_method = "extend_fallback"
                        stats["extend_fallback_count"] += 1
                    else:
                        fallback_clip = clips[0]
                        clip = fallback_clip
                        source_start = 0
                        source_end = min(line_duration, fallback_clip.get("duration", line_duration))
                        confidence = 0.1
                        reason = "No suitable clip found, using fallback"
                        selection_method = "hard_fallback"
                        stats["hard_fallback_count"] += 1
                    clip_result = (clip, source_start, source_end, confidence, reason)

            if clip_result:
                clip, source_start, source_end, confidence, reason = clip_result

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
                    selection_method=selection_method,
                )
                timeline_events.append(asdict(event))

                clip_id = clip.get("clip_id", "unknown")
                used_clips[clip_id] = used_clips.get(clip_id, 0) + 1
                prev_clip = clip
                prev_source_start = source_start
                prev_source_end = source_end

                logger.info(
                    "Event %d: lyric='%s' clip=%s method=%s confidence=%.3f",
                    len(timeline_events) - 1,
                    line.get("text", "")[:30],
                    clip_id[:20],
                    selection_method,
                    confidence,
                )

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
                "segment_match_count": stats["segment_match_count"],
                "semantic_match_count": stats["semantic_match_count"],
                "extend_fallback_count": stats["extend_fallback_count"],
                "hard_fallback_count": stats["hard_fallback_count"],
                "low_confidence_count": stats["low_confidence_count"],
                "avg_confidence": round(
                    sum(e["confidence"] for e in timeline_events) / max(len(timeline_events), 1),
                    3,
                ),
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
        """Find the BEST matching segment across all clips for a lyric."""
        lyric_text = lyric_line.get("text", "")
        matches = segment_matches.get(lyric_text, [])

        best_result = None
        best_score = -1

        for match in matches:
            score = match.get("score", 0)
            if score < 0.05:
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
            confidence = score * repetition_penalty

            if confidence > best_score:
                best_score = confidence
                actual_end = min(seg_start + required_duration, clip.get("duration", seg_end))
                caption = match.get("caption", "")
                reason = f"Segment match: \"{caption}\" (score: {score:.2f}, used: {times_used}x)"
                best_result = (clip, seg_start, actual_end, confidence, reason)

        return best_result

    def _generate_beat_grid(self, beats: List[float], duration: float) -> List[Dict]:
        """Generate lyric-line-style grid from beat timestamps (2 beats per event)."""
        lines = []
        i = 0
        while i < len(beats) - 1:
            start = beats[i]
            end = beats[min(i + 2, len(beats) - 1)]
            if start >= duration:
                break
            lines.append({
                "text": f"[beat {i // 2 + 1}]",
                "section": "beat-synced",
                "start": round(start, 3),
                "end": round(end, 3),
                "importance": 0.5,
            })
            i += 2
        return lines

    def _generate_segment_grid(self, duration: float, segment_length: float = 3.0) -> List[Dict]:
        """Generate fixed-duration segments as fallback grid."""
        lines = []
        current = 0.0
        idx = 1
        while current < duration:
            end = min(current + segment_length, duration)
            lines.append({
                "text": f"[segment {idx}]",
                "section": "auto-segment",
                "start": round(current, 3),
                "end": round(end, 3),
                "importance": 0.5,
            })
            current = end
            idx += 1
        return lines

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
