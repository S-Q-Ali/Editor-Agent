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
    clip_caption: str = ""


class EditingBrain:
    def __init__(self):
        self.transitions = ["cut", "fade", "crossfade", "dissolve"]
        self.max_repetition = 4
        self.confidence_threshold = 0.10
        self._fallback_idx = 0
        self.min_event_duration = 2.0

    def generate_timeline(
        self,
        music_analysis: Dict,
        lyrics_alignment: Dict,
        clips: List[Dict],
        lyrics_matches: Dict,
        segment_matches: Optional[Dict] = None,
        clip_matches: Optional[Dict] = None,
        mode: str = "auto",
        clip_order: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        if mode == "sequential" and clip_order:
            return self.generate_sequential_timeline(
                music_analysis, lyrics_alignment, clips, clip_order,
                clip_matches=clip_matches, segment_matches=segment_matches,
            )
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
            "clip_match_count": 0,
            "best_available_count": 0,
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

            # Priority 1: CLIP-level whole-clip matching (best quality)
            if clip_matches:
                clip_result = self._select_clip_from_clip_matches(
                    line, clips, clip_matches, segment_matches, used_clips, line_duration, beats
                )
                if clip_result:
                    selection_method = "clip_match"
                    stats.setdefault("clip_match_count", 0)
                    stats["clip_match_count"] += 1

            # Priority 2: Best available clip (no matching, just pick highest quality unused)
            if not clip_result:
                clip_result = self._select_best_available_clip(
                    clips, used_clips, line_duration, beats
                )
                if clip_result:
                    selection_method = "best_available"
                    stats.setdefault("best_available_count", 0)
                    stats["best_available_count"] += 1

            if clip_result:
                clip, source_start, source_end, confidence, reason = clip_result
                if confidence < self.confidence_threshold and prev_clip is not None:
                    # Try to find the best unused clip instead of extending
                    best_alt = None
                    best_alt_score = -1
                    for c in clips:
                        cid = c.get("clip_id", "unknown")
                        if used_clips.get(cid, 0) >= self.max_repetition:
                            continue
                        qual = c.get("quality_score", 0.5)
                        if qual > best_alt_score:
                            best_alt_score = qual
                            best_alt = c
                    if best_alt:
                        clip = best_alt
                        source_start = self._snap_to_beats(0, beats)
                        source_end = min(line_duration, clip.get("duration", line_duration))
                        confidence = max(0.1, confidence)
                        reason = f"Fallback to best unused clip (score: {confidence:.2f})"
                        selection_method = "extend_fallback"
                        stats["extend_fallback_count"] += 1
                        stats["low_confidence_count"] += 1
                    else:
                        # All clips at max repetition — cycle through clips round-robin
                        clip = clips[self._fallback_idx % len(clips)]
                        self._fallback_idx += 1
                        source_start = self._snap_to_beats(0, beats)
                        source_end = min(line_duration, clip.get("duration", line_duration))
                        confidence = max(0.05, confidence * 0.5)
                        reason = f"All clips used, cycling (score: {confidence:.2f})"
                        selection_method = "extend_fallback"
                        stats["extend_fallback_count"] += 1
                        stats["low_confidence_count"] += 1
                else:
                    source_start = self._snap_to_beats(source_start, beats)
            else:
                if clips:
                    fallback_clip = clips[self._fallback_idx % len(clips)]
                    self._fallback_idx += 1
                    clip = fallback_clip
                    source_start = self._snap_to_beats(0, beats)
                    source_end = min(line_duration, clip.get("duration", line_duration))
                    confidence = 0.05
                    reason = "No match, cycling clips"
                    selection_method = "hard_fallback"
                    stats["hard_fallback_count"] += 1
                    clip_result = (clip, source_start, source_end, confidence, reason)

            if clip_result:
                clip, source_start, source_end, confidence, reason = clip_result

                clip_caption = self._lookup_clip_caption(clip, source_start, source_end)

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
                    clip_caption=clip_caption,
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

        if current_time < duration and clips:
            remaining = duration - current_time
            fallback_clip = clips[self._fallback_idx % len(clips)]
            self._fallback_idx += 1
            clip_id = fallback_clip.get("clip_id", "unknown")
            clip_duration = fallback_clip.get("duration", remaining)
            source_start = self._snap_to_beats(0, beats)
            source_end = min(remaining, clip_duration)
            tail_caption = self._lookup_clip_caption(fallback_clip, source_start, source_end)
            timeline_events.append({
                "clip_id": clip_id,
                "source_start": round(source_start, 3),
                "source_end": round(source_end, 3),
                "timeline_start": round(current_time, 3),
                "timeline_end": round(duration, 3),
                "transition": "fade",
                "reason": f"Tail fill: remaining {remaining:.1f}s",
                "confidence": 0.3,
                "lyric_text": "[tail]",
                "selection_method": "hard_fallback",
                "clip_caption": tail_caption,
            })

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
                "clip_match_count": stats["clip_match_count"],
                "best_available_count": stats["best_available_count"],
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

    def generate_sequential_timeline(
        self,
        music_analysis: Dict,
        lyrics_alignment: Dict,
        clips: List[Dict],
        clip_order: List[Dict],
        clip_matches: Optional[Dict] = None,
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

        ordered_clips = self._build_ordered_clip_list(clips, clip_order)
        if not ordered_clips:
            return self._generate_empty_timeline(duration)

        grouped = self._group_lyrics_into_phrases(lyrics_lines, beats)
        self._assign_durations(grouped, duration, beats)

        events = []
        used_ranges: Dict[str, List[tuple]] = {}
        current_time = 0.0
        clip_idx = 0
        stats = {
            "sequential_count": 0,
            "clip_match_count": 0,
            "hard_fallback_count": 0,
        }

        for phrase in grouped:
            if current_time >= duration:
                break

            phrase_duration = phrase["duration"]
            if phrase_duration < self.min_event_duration:
                phrase_duration = self.min_event_duration

            clip = ordered_clips[clip_idx % len(ordered_clips)]
            clip_id = clip.get("clip_id", "unknown")
            clip_duration = clip.get("duration", 15)

            source_start, source_end, confidence = self._pick_sequential_range(
                clip, phrase, used_ranges, phrase_duration, beats
            )

            used_ranges.setdefault(clip_id, []).append((source_start, source_end))

            clip_caption = self._lookup_clip_caption(clip, source_start, source_end)

            event = {
                "clip_id": clip_id,
                "source_start": round(source_start, 3),
                "source_end": round(source_end, 3),
                "timeline_start": round(current_time, 3),
                "timeline_end": round(current_time + phrase_duration, 3),
                "transition": self._select_transition(current_time, sections),
                "reason": f"Sequential: phrase '{phrase['text'][:40]}' → clip '{clip_id}'",
                "confidence": round(confidence, 3),
                "lyric_text": phrase["text"],
                "selection_method": "sequential",
                "clip_caption": clip_caption,
            }
            events.append(event)
            stats["sequential_count"] += 1

            clip_idx += 1

            logger.info(
                "Sequential event %d: phrase='%s' clip=%s range=[%.1f-%.1f] confidence=%.3f",
                len(events) - 1,
                phrase["text"][:30],
                clip_id[:20],
                source_start,
                source_end,
                confidence,
            )

            current_time += phrase_duration

        if current_time < duration and ordered_clips:
            remaining = duration - current_time
            clip = ordered_clips[clip_idx % len(ordered_clips)]
            clip_id = clip.get("clip_id", "unknown")
            clip_duration = clip.get("duration", 15)
            source_start, source_end, confidence = self._pick_sequential_range(
                clip, {"text": "[tail]", "duration": remaining}, used_ranges, remaining, beats
            )
            tail_caption = self._lookup_clip_caption(clip, source_start, source_end)
            events.append({
                "clip_id": clip_id,
                "source_start": round(source_start, 3),
                "source_end": round(source_end, 3),
                "timeline_start": round(current_time, 3),
                "timeline_end": round(duration, 3),
                "transition": "fade",
                "reason": f"Sequential tail fill: remaining {remaining:.1f}s",
                "confidence": round(confidence, 3),
                "lyric_text": "[tail]",
                "selection_method": "sequential",
                "clip_caption": tail_caption,
            })

        timeline = {
            "version": 1,
            "duration": duration,
            "total_events": len(events),
            "tracks": {"video": events, "audio": []},
            "metadata": {
                "mode": "sequential",
                "bpm": music_analysis.get("bpm", 0),
                "sections_count": len(sections),
                "lyrics_lines": len(lyrics_lines),
                "grouped_phrases": len(grouped),
                "clips_available": len(ordered_clips),
                "clips_used": len(set(e["clip_id"] for e in events)),
                "sequential_count": stats["sequential_count"],
                "avg_confidence": round(
                    sum(e["confidence"] for e in events) / max(len(events), 1), 3
                ),
            },
        }
        return timeline

    def _build_ordered_clip_list(self, clips: List[Dict], clip_order: List[Dict]) -> List[Dict]:
        order_map = {c["filename"]: c["index"] for c in clip_order}
        sorted_clips = sorted(
            clips,
            key=lambda c: order_map.get(c.get("filename", ""), 999)
        )
        return sorted_clips

    def _group_lyrics_into_phrases(
        self, lyrics_lines: List[Dict], beats: List[float]
    ) -> List[Dict]:
        if not lyrics_lines:
            return []

        min_duration = self.min_event_duration
        gap_threshold = 0.5
        max_phrase_duration = 4.0

        phrases = []
        current_phrase = None

        for line in lyrics_lines:
            text = line.get("text", "").strip()
            start = line.get("start", 0)
            end = line.get("end", start + 1.0)
            line_duration = end - start

            if line_duration <= 0:
                line_duration = 1.0

            if current_phrase is None:
                current_phrase = {
                    "text": text,
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "lines": [line],
                }
                continue

            gap = start - current_phrase["end"]
            combined_duration = end - current_phrase["start"]

            should_merge = (
                gap <= gap_threshold
                and combined_duration <= max_phrase_duration
                and (current_phrase["duration"] < min_duration or line_duration < min_duration)
            )

            if should_merge:
                current_phrase["text"] += ", " + text
                current_phrase["end"] = end
                current_phrase["duration"] = end - current_phrase["start"]
                current_phrase["lines"].append(line)
            else:
                if current_phrase["duration"] < min_duration:
                    current_phrase["duration"] = min_duration
                phrases.append(current_phrase)
                current_phrase = {
                    "text": text,
                    "start": start,
                    "end": end,
                    "duration": end - start,
                    "lines": [line],
                }

        if current_phrase:
            if current_phrase["duration"] < min_duration:
                current_phrase["duration"] = min_duration
            phrases.append(current_phrase)

        return phrases

    def _assign_durations(
        self, phrases: List[Dict], total_duration: float, beats: List[float]
    ):
        beat_duration = 60.0 / max(beats[1] - beats[0], 0.3) if len(beats) > 1 else 2.0
        min_event = max(self.min_event_duration, beat_duration * 4)

        for phrase in phrases:
            if phrase["duration"] < min_event:
                phrase["duration"] = min_event

        total_assigned = sum(p["duration"] for p in phrases)
        if total_assigned < total_duration and phrases:
            scale = total_duration / total_assigned
            for phrase in phrases:
                phrase["duration"] = round(phrase["duration"] * scale, 3)

    def _pick_sequential_range(
        self,
        clip: Dict,
        phrase: Dict,
        used_ranges: Dict[str, List[tuple]],
        required_duration: float,
        beats: List[float],
    ) -> tuple:
        clip_id = clip.get("clip_id", "unknown")
        clip_duration = clip.get("duration", 15)
        already_used = used_ranges.get(clip_id, [])

        best_segments = clip.get("best_segments", [])

        if best_segments:
            for seg in best_segments:
                seg_start = seg.get("start", 0)
                seg_end = seg.get("end", clip_duration)
                seg_duration = seg_end - seg_start

                if seg_duration < required_duration * 0.5:
                    continue

                overlap = False
                for used_start, used_end in already_used:
                    if seg_start < used_end and seg_end > used_start:
                        overlap = True
                        break

                if not overlap:
                    source_start = self._snap_to_beats(seg_start, beats)
                    source_end = min(source_start + required_duration, clip_duration)
                    if source_end - source_start >= required_duration * 0.5:
                        confidence = 0.7 + seg.get("score", 0) * 0.3
                        return source_start, source_end, confidence

        num_segments = max(1, int(clip_duration / max(required_duration, 1.0)))
        for i in range(num_segments):
            seg_start = i * (clip_duration / num_segments)
            seg_end = min(seg_start + required_duration, clip_duration)

            overlap = False
            for used_start, used_end in already_used:
                if seg_start < used_end and seg_end > used_start:
                    overlap = True
                    break

            if not overlap:
                source_start = self._snap_to_beats(seg_start, beats)
                source_end = min(source_start + required_duration, clip_duration)
                return source_start, source_end, 0.5

        source_start = 0
        source_end = min(required_duration, clip_duration)
        return source_start, source_end, 0.3

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

    def _select_best_available_clip(
        self,
        clips: List[Dict],
        used_clips: Dict,
        required_duration: float,
        beats: List[float],
    ) -> Optional[tuple]:
        """Pick the highest-quality unused clip without any matching logic."""
        candidates = []
        for clip in clips:
            clip_id = clip.get("clip_id", "unknown")
            times_used = used_clips.get(clip_id, 0)
            if times_used >= self.max_repetition:
                continue
            quality = clip.get("quality_score", 0.5)
            repetition_penalty = max(0.1, 1.0 - times_used * 0.15)
            candidates.append((clip, quality * repetition_penalty))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[1], reverse=True)
        clip, score = candidates[0]
        clip_id = clip.get("clip_id", "unknown")
        clip_duration = clip.get("duration", 0)
        times_used = used_clips.get(clip_id, 0)

        # Use best segment within clip if available
        best_segments = clip.get("best_segments", [])
        if best_segments:
            best_seg = best_segments[0]
            source_start = self._snap_to_beats(best_seg.get("start", 0), beats)
            source_end = min(source_start + required_duration, clip_duration)
            return (clip, source_start, source_end, score, f"Best available clip (quality: {score:.2f}, used: {times_used}x)")

        source_start = self._snap_to_beats(0, beats)
        source_end = min(source_start + required_duration, clip_duration)
        return (clip, source_start, source_end, score, f"Best available clip (quality: {score:.2f}, used: {times_used}x)")

    def _select_clip_from_clip_matches(
        self,
        lyric_line: Dict,
        clips: List[Dict],
        clip_matches: Dict,
        segment_matches: Optional[Dict],
        used_clips: Dict,
        required_duration: float,
        beats: List[float],
    ) -> Optional[tuple]:
        """Select a clip using whole-clip CLIP matching, then find best segment within it."""
        lyric_text = lyric_line.get("text", "")
        matches = clip_matches.get(lyric_text, [])

        for match in matches:
            score = match.get("score", 0)
            if score < 0.02:
                continue

            clip_id = match.get("clip_id", "")
            clip = next((c for c in clips if c.get("clip_id") == clip_id), None)
            if not clip:
                continue

            times_used = used_clips.get(clip_id, 0)
            if times_used >= self.max_repetition:
                continue

            repetition_penalty = max(0.1, 1.0 - times_used * 0.15)
            confidence = score * repetition_penalty

            # Find best segment within this clip for source range
            source_start, source_end = self._find_best_segment_in_clip(
                clip, lyric_text, segment_matches, required_duration, beats
            )

            scene_desc = match.get("scene_description", "")[:50]
            reason = f"Clip match: \"{scene_desc}\" (score: {score:.2f}, used: {times_used}x)"
            return (clip, source_start, source_end, confidence, reason)

        return None

    def _find_best_segment_in_clip(
        self,
        clip: Dict,
        lyric_text: str,
        segment_matches: Optional[Dict],
        required_duration: float,
        beats: List[float],
    ) -> tuple:
        """Find the best source range within a matched clip."""
        clip_duration = clip.get("duration", 0)
        segment_embeddings = clip.get("segment_embeddings", clip.get("segment_descriptions", []))

        # Try to find the best segment within this clip from segment_matches
        best_seg_start = 0
        best_seg_score = -1

        if segment_matches and lyric_text in segment_matches:
            for seg_match in segment_matches[lyric_text]:
                if seg_match.get("clip_id") == clip.get("clip_id"):
                    seg_score = seg_match.get("score", 0)
                    if seg_score > best_seg_score:
                        best_seg_score = seg_score
                        best_seg_start = seg_match.get("segment_start", 0)

        # If no segment match found, use the highest-quality segment
        if best_seg_score < 0 and segment_embeddings:
            best_seg = max(segment_embeddings, key=lambda s: s.get("score", 0))
            best_seg_start = best_seg.get("start", 0)

        # Snap start to nearest beat
        source_start = self._snap_to_beats(best_seg_start, beats)

        # Ensure we have enough duration
        actual_end = min(source_start + required_duration, clip_duration)
        if actual_end - source_start < required_duration * 0.5:
            source_start = max(0, actual_end - required_duration)
            source_start = self._snap_to_beats(source_start, beats)
            actual_end = min(source_start + required_duration, clip_duration)

        return source_start, actual_end

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

    def _lookup_clip_caption(
        self, clip: Dict, source_start: float, source_end: float
    ) -> str:
        segment_descriptions = clip.get("segment_descriptions", [])
        if not segment_descriptions:
            return clip.get("scene_description", "")

        best_caption = ""
        best_overlap = 0

        for seg in segment_descriptions:
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            overlap_start = max(source_start, seg_start)
            overlap_end = min(source_end, seg_end)
            overlap = max(0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_caption = seg.get("caption", "")

        if not best_caption:
            best_caption = clip.get("scene_description", "")

        return best_caption

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
