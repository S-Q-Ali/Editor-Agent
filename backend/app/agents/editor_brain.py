import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

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
    section: str = ""
    selection_method: str = ""
    clip_caption: str = ""
    auto_generated: bool = False


def _normalize_text(text: str) -> str:
    """Normalize lyric text for repetition grouping."""
    return re.sub(r"[^a-z0-9 ]+", "", (text or "").lower()).strip()


class EditingBrain:
    def __init__(self):
        # Repetition is now tracked per (clip, source-window), not per clip.
        # max_clip_usage is a safety cap on how many events a single clip may serve.
        self.max_clip_usage = 8
        # Minimum whole-clip match score to treat a match as confident.
        self.confidence_threshold = 0.15
        self.min_event_duration = 2.0
        self.max_event_duration = 8.0
        # Fraction of an event's duration allowed to overlap an already-used
        # window of the same clip before the window counts as "reused".
        self.window_overlap_limit = 0.5

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
        return self._generate_auto_timeline(
            music_analysis, lyrics_alignment, clips, clip_matches, segment_matches
        )

    # ------------------------------------------------------------------
    # AUTO mode: lyric-anchored timeline with two-stage matching
    # Stage 1: repeated lyrics are grouped; each group gets a primary clip
    #          plus alternates (consistent visual motif per lyric).
    # Stage 2: within the chosen clip, the best unused source window is
    #          selected ("trim from anywhere") — segment boundaries,
    #          quality/motion, beat alignment and window freshness.
    # ------------------------------------------------------------------

    def _generate_auto_timeline(
        self,
        music_analysis: Dict,
        lyrics_alignment: Dict,
        clips: List[Dict],
        clip_matches: Optional[Dict],
        segment_matches: Optional[Dict],
    ) -> Dict[str, Any]:
        duration = music_analysis.get("duration", 0)
        beats = music_analysis.get("beats", [])
        sections = music_analysis.get("sections", [])
        lyrics_lines = lyrics_alignment.get("lines", [])

        if not clips or duration <= 0:
            return self._generate_empty_timeline(duration)

        if not lyrics_lines:
            if beats and len(beats) > 1:
                lyrics_lines = self._generate_beat_grid(beats, duration)
            else:
                lyrics_lines = self._generate_segment_grid(duration)

        phrases = self._group_lyrics_into_phrases(lyrics_lines, beats)
        slots = self._build_lyric_slots(phrases, duration)

        used_windows: Dict[str, List[Tuple[float, float]]] = {}
        group_candidates: Dict[str, List[Tuple[Dict, float, str]]] = {}
        stats = {
            "clip_match_count": 0,
            "clip_match_low_count": 0,
            "best_available_count": 0,
            "filler_count": 0,
            "window_reuse_count": 0,
        }

        events: List[Dict] = []
        prev_clip_id: Optional[str] = None

        for slot in slots:
            kind = slot["kind"]
            for chunk_offset, chunk_dur in self._split_chunks(slot["end"] - slot["start"]):
                tl_start = round(slot["start"] + chunk_offset, 3)
                tl_end = round(tl_start + chunk_dur, 3)

                clip, confidence, reason, method = self._select_clip_for_slot(
                    slot, clips, clip_matches or {}, used_windows,
                    prev_clip_id, group_candidates, stats,
                )
                source_start, source_end, reused = self._pick_window(
                    clip, chunk_dur, used_windows, beats
                )
                if reused:
                    stats["window_reuse_count"] += 1
                used_windows.setdefault(clip["clip_id"], []).append(
                    (source_start, source_end)
                )

                events.append({
                    "clip_id": clip["clip_id"],
                    "source_start": round(source_start, 3),
                    "source_end": round(source_end, 3),
                    "timeline_start": tl_start,
                    "timeline_end": tl_end,
                    "transition": "fade" if kind in ("intro", "outro") else "cut",
                    "reason": reason,
                    "confidence": round(confidence, 3),
                    "lyric_text": slot["text"] if kind == "lyric" else f"[{kind}]",
                    "section": slot.get("section", ""),
                    "selection_method": method if kind == "lyric" else kind,
                    "clip_caption": self._lookup_clip_caption(clip, source_start, source_end),
                    "auto_generated": True,
                })
                prev_clip_id = clip["clip_id"]
                logger.info(
                    "Event %d [%s] %.2f-%.2fs: clip=%s window=[%.2f-%.2f] method=%s conf=%.3f lyric='%s'",
                    len(events) - 1, kind, tl_start, tl_end, clip["clip_id"],
                    source_start, source_end, method, confidence, slot["text"][:40],
                )

        avg_confidence = round(
            sum(e["confidence"] for e in events) / max(len(events), 1), 3
        )
        return {
            "version": 2,
            "mode": "auto",
            "duration": round(duration, 3),
            "total_events": len(events),
            "tracks": {"video": events, "audio": []},
            "metadata": {
                "mode": "auto",
                "bpm": music_analysis.get("bpm", 0),
                "sections_count": len(sections),
                "lyrics_lines": len(lyrics_lines),
                "lyric_phrases": len(phrases),
                "clips_used": len({e["clip_id"] for e in events}),
                **stats,
                "avg_confidence": avg_confidence,
                "min_event_duration": self.min_event_duration,
                "max_event_duration": self.max_event_duration,
            },
        }

    def _build_lyric_slots(self, phrases: List[Dict], duration: float) -> List[Dict]:
        """Anchor each phrase at its REAL timestamp.

        - Intro slot covers the instrumental before the first lyric.
        - Short pauses between phrases extend (hold) the previous shot.
        - Longer pauses get a music-fill slot with a different clip.
        - Outro slot covers the tail after the last lyric.
        """
        min_dur = self.min_event_duration
        raw: List[Dict] = []
        for phrase in phrases:
            start = float(phrase.get("start", 0.0))
            end = float(phrase.get("end", start + min_dur))
            if end - start < min_dur:
                end = start + min_dur
            start = max(0.0, start)
            end = min(end, duration)
            if start >= duration or end - start < 0.5:
                continue
            lines = phrase.get("lines") or [{}]
            raw.append({
                "text": phrase.get("text", ""),
                "key_text": lines[0].get("text", phrase.get("text", "")),
                "start": round(start, 3),
                "end": round(end, 3),
                "kind": "lyric",
                "section": phrase.get("section", ""),
            })
        if not raw:
            return []

        slots: List[Dict] = []
        if raw[0]["start"] > 0.05:
            slots.append({"text": "intro", "key_text": None, "start": 0.0,
                          "end": raw[0]["start"], "kind": "intro"})

        for slot in raw:
            if slots and slot["start"] < slots[-1]["end"] - 0.01:
                # Overlapping phrases (min-duration extension ran into the next
                # anchor): never allow timeline overlap — it desyncs concat.
                prev = slots[-1]
                if prev["kind"] == "lyric" and \
                        (slot["start"] - prev["start"]) >= 1.0:
                    prev["end"] = slot["start"]  # trim the hold, keep >= 1s
                else:
                    # Too short to trim: delay this slot slightly instead
                    slot["start"] = slots[-1]["end"]
                    slot["end"] = max(slot["end"], slot["start"] + 1.0)
            if slots and slot["start"] > slots[-1]["end"] + 0.01:
                prev = slots[-1]
                gap = slot["start"] - prev["end"]
                prev_len = prev["end"] - prev["start"]
                if prev["kind"] == "lyric" and prev_len + gap <= self.max_event_duration:
                    prev["end"] = slot["start"]  # hold previous shot through the pause
                else:
                    slots.append({"text": "music", "key_text": None,
                                  "start": prev["end"], "end": slot["start"],
                                  "kind": "music"})
            slots.append(slot)

        if slots[-1]["end"] < duration - 0.05:
            slots.append({"text": "outro", "key_text": None,
                          "start": slots[-1]["end"], "end": duration,
                          "kind": "outro"})
        return slots

    def _split_chunks(self, duration: float) -> List[Tuple[float, float]]:
        """Split a slot into equal chunks of at most max_event_duration."""
        if duration <= self.max_event_duration + 1e-6:
            return [(0.0, round(duration, 3))]
        n = int(duration / self.max_event_duration)
        if duration % self.max_event_duration > 1e-6:
            n += 1
        chunk = duration / n
        return [(round(i * chunk, 3), round(chunk, 3)) for i in range(n)]

    def _select_clip_for_slot(
        self,
        slot: Dict,
        clips: List[Dict],
        clip_matches: Dict,
        used_windows: Dict[str, List[Tuple[float, float]]],
        prev_clip_id: Optional[str],
        group_candidates: Dict[str, List[Tuple[Dict, float, str]]],
        stats: Dict,
    ) -> Tuple[Dict, float, str, str]:
        kind = slot["kind"]
        required = slot["end"] - slot["start"]

        if kind != "lyric":
            clip = self._pick_filler_clip(clips, used_windows, required, prev_clip_id)
            stats["filler_count"] += 1
            return clip, 0.2, f"{kind.capitalize()} fill: best available clip", kind

        key_text = slot.get("key_text") or slot["text"]
        if key_text not in group_candidates:
            group_candidates[key_text] = self._resolve_group_candidates(
                key_text, clips, clip_matches
            )
        candidates = group_candidates[key_text]

        deferred: Optional[Tuple[Dict, float, str]] = None
        for clip, score, method in candidates:
            cid = clip.get("clip_id", "unknown")
            if len(used_windows.get(cid, [])) >= self.max_clip_usage:
                continue
            if self._window_freshness(clip, required, used_windows) > self.window_overlap_limit:
                continue
            if cid == prev_clip_id:
                if deferred is None:
                    deferred = (clip, score, method)
                continue
            stats[self._stat_key(method)] += 1
            reason = (f"Lyric group '{_normalize_text(key_text)[:30]}' -> clip {cid} "
                      f"({method}, score {score:.2f})")
            return clip, self._confidence_for(method, score), reason, method

        # Only fresh option is the previous clip — allowed (window still fresh)
        if deferred is not None:
            clip, score, method = deferred
            stats[self._stat_key(method)] += 1
            reason = (f"Lyric group '{_normalize_text(key_text)[:30]}' -> clip "
                      f"{clip.get('clip_id')} ({method}, score {score:.2f})")
            return clip, self._confidence_for(method, score), reason, method

        # Window pool exhausted for this group: reuse windows (sync preserved)
        for clip, score, method in candidates:
            cid = clip.get("clip_id", "unknown")
            if len(used_windows.get(cid, [])) >= self.max_clip_usage:
                continue
            stats[self._stat_key(method)] += 1
            confidence = self._confidence_for(method, score) * 0.7
            reason = (f"Lyric group '{_normalize_text(key_text)[:30]}' -> clip {cid} "
                      f"({method}, score {score:.2f}, window reused)")
            return clip, confidence, reason, method

        clip = clips[0]
        return clip, 0.05, "Hard fallback: first clip", "hard_fallback"

    @staticmethod
    def _stat_key(method: str) -> str:
        if method == "clip_match":
            return "clip_match_count"
        if method == "clip_match_low":
            return "clip_match_low_count"
        return "best_available_count"

    def _confidence_for(self, method: str, score: float) -> float:
        if method == "clip_match":
            return max(0.05, min(score, 1.0))
        if method == "clip_match_low":
            return max(0.05, score * 0.5)
        return max(0.05, score * 0.4)

    def _resolve_group_candidates(
        self, key_text: str, clips: List[Dict], clip_matches: Dict
    ) -> List[Tuple[Dict, float, str]]:
        """Primary + alternate clips for a repeated-lyric group."""
        clip_by_id = {c.get("clip_id", "unknown"): c for c in clips}
        candidates: List[Tuple[Dict, float, str]] = []
        seen = set()

        for m in sorted(clip_matches.get(key_text, []) or [],
                        key=lambda x: -float(x.get("score", 0))):
            cid = m.get("clip_id", "")
            clip = clip_by_id.get(cid)
            if clip is None or cid in seen:
                continue
            seen.add(cid)
            score = float(m.get("score", 0))
            method = "clip_match" if score >= self.confidence_threshold else "clip_match_low"
            candidates.append((clip, score, method))

        for clip in sorted(
            clips,
            key=lambda c: (-(c.get("quality_score") or 0.5), c.get("clip_id", "unknown")),
        ):
            cid = clip.get("clip_id", "unknown")
            if cid in seen:
                continue
            seen.add(cid)
            candidates.append((clip, float(clip.get("quality_score") or 0.5), "best_available"))
        return candidates

    def _pick_filler_clip(
        self,
        clips: List[Dict],
        used_windows: Dict[str, List[Tuple[float, float]]],
        required: float,
        prev_clip_id: Optional[str],
    ) -> Dict:
        """Deterministic filler pick: freshest window, least used, best quality."""
        def sort_key(c: Dict):
            cid = c.get("clip_id", "unknown")
            fresh = self._window_freshness(c, required, used_windows) <= self.window_overlap_limit
            usage = len(used_windows.get(cid, []))
            return (0 if fresh else 1, 1 if cid == prev_clip_id else 0, usage,
                    -(c.get("quality_score") or 0.5), cid)
        return sorted(clips, key=sort_key)[0]

    def _candidate_starts(self, clip: Dict, required: float) -> List[float]:
        """All candidate window start positions inside a clip (trim from anywhere)."""
        clip_dur = float(clip.get("duration", 0) or 0)
        if clip_dur <= 0:
            return [0.0]
        max_start = max(0.0, clip_dur - required)
        starts = set()
        for seg in clip.get("segment_descriptions", []) or []:
            try:
                s = float(seg.get("start", 0) or 0)
            except (TypeError, ValueError):
                continue
            starts.add(round(min(max(0.0, s), max_start), 3))
        for seg in clip.get("best_segments", []) or []:
            try:
                s = float(seg.get("start", 0) or 0)
            except (TypeError, ValueError):
                continue
            starts.add(round(min(max(0.0, s), max_start), 3))
        t = 0.0
        while t <= max_start + 1e-6:
            starts.add(round(t, 3))
            t += 1.0
        if not starts:
            starts.add(0.0)
        return sorted(starts)

    @staticmethod
    def _overlap_amount(start: float, end: float,
                        used: List[Tuple[float, float]]) -> float:
        total = 0.0
        for us, ue in used:
            total += max(0.0, min(end, ue) - max(start, us))
        return total

    def _window_freshness(
        self,
        clip: Dict,
        required: float,
        used_windows: Dict[str, List[Tuple[float, float]]],
    ) -> float:
        """Best achievable overlap fraction with used windows of this clip.
        0.0 = a fully fresh window is still available."""
        used = used_windows.get(clip.get("clip_id", "unknown"), [])
        if not used or required <= 0:
            return 0.0
        best: Optional[float] = None
        for s in self._candidate_starts(clip, required):
            ov = min(self._overlap_amount(s, s + required, used), required)
            frac = ov / required
            if best is None or frac < best:
                best = frac
                if best == 0.0:
                    break
        return best if best is not None else 1.0

    def _pick_window(
        self,
        clip: Dict,
        required: float,
        used_windows: Dict[str, List[Tuple[float, float]]],
        beats: List[float],
    ) -> Tuple[float, float, bool]:
        """Stage 2 of matching: pick the best source window inside the clip.

        Prefers windows that (a) don't overlap already-used windows,
        (b) cover high-motion/high-quality segments, (c) start on a beat.
        Returns (start, end, reused)."""
        clip_dur = float(clip.get("duration", 0) or 0)
        if clip_dur <= 0:
            return 0.0, round(max(required, 0.5), 3), False
        required = min(required, clip_dur)
        used = used_windows.get(clip.get("clip_id", "unknown"), [])
        max_start = max(0.0, clip_dur - required)

        best: Optional[Tuple[float, float, float]] = None  # (overlap, -motion, start)
        for s in self._candidate_starts(clip, required):
            s = min(max(0.0, self._snap_to_beats(s, beats, tolerance=0.2)), max_start)
            e = s + required
            ov = min(self._overlap_amount(s, e, used), required)
            motion = 0.0
            for seg in clip.get("best_segments", []) or []:
                seg_s = float(seg.get("start", 0) or 0)
                seg_e = float(seg.get("end", 0) or 0)
                motion += max(0.0, min(e, seg_e) - max(s, seg_s)) * float(seg.get("score", 0) or 0)
            key = (ov, -motion, s)
            if best is None or key < best:
                best = key
        if best is None:
            return 0.0, round(required, 3), False

        start = best[2]
        end = min(start + required, clip_dur)
        if end - start < required - 0.05:
            start = max(0.0, clip_dur - required)
            end = clip_dur
        reused = best[0] > self.window_overlap_limit * required
        return round(start, 3), round(end, 3), reused

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
                "section": phrase.get("section", ""),
                "selection_method": "sequential",
                "clip_caption": clip_caption,
                "auto_generated": True,
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
                "section": "",
                "selection_method": "sequential",
                "clip_caption": tail_caption,
                "auto_generated": True,
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
                    "section": line.get("section", ""),
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
                    "section": line.get("section", ""),
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

    def _select_transition(self, current_time: float, sections: List[Dict],
                           kind: str = "lyric") -> str:
        """Deterministic transition selection (no randomness).
        Note: the current concat renderer supports cuts and fades only."""
        if kind in ("intro", "outro"):
            return "fade"
        for section in sections:
            if section["start"] <= current_time <= section["end"]:
                label = section.get("label", "").lower()
                if "bridge" in label or "intro" in label or "outro" in label:
                    return "fade"
                return "cut"
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

            src_dur = event["source_end"] - event["source_start"]
            tl_dur = event["timeline_end"] - event["timeline_start"]
            if abs(src_dur - tl_dur) > 0.25:
                errors.append(
                    f"Event {i}: source duration {src_dur:.2f}s != timeline duration {tl_dur:.2f}s"
                )

            if tl_dur < 1.0:
                warnings.append(f"Event {i}: very short event ({tl_dur:.2f}s)")

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
