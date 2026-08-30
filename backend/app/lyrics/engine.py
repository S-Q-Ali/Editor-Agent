import re
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import subprocess


class LyricsEngine:
    def __init__(self):
        self.section_markers = [
            "Intro", "Verse", "Chorus", "Bridge", "Outro",
            "Pre-Chorus", "Post-Chorus", "Hook", "Refrain",
            "Interlude", "Solo", "Coda"
        ]

    def parse_lyrics(self, text: str) -> List[Dict[str, Any]]:
        lines = []
        current_section = "Unknown"

        for line_text in text.strip().split("\n"):
            line_text = line_text.strip()
            if not line_text:
                continue

            if self._is_section_header(line_text):
                current_section = self._extract_section_name(line_text)
                continue

            clean_text = self._clean_lyric_line(line_text)
            if clean_text:
                lines.append({
                    "text": clean_text,
                    "section": current_section,
                    "timestamp": None,
                    "importance": self._estimate_importance(clean_text),
                })

        return lines

    def align_with_audio(self, lyrics: List[Dict], audio_analysis: Dict) -> List[Dict]:
        duration = audio_analysis.get("duration", 0)
        sections = audio_analysis.get("sections", [])
        beats = audio_analysis.get("beats", [])

        if not lyrics:
            return []

        if not sections and not beats:
            return self._evenly_distribute(lyrics, duration)

        if sections:
            return self._align_with_sections(lyrics, sections)
        else:
            return self._align_with_beats(lyrics, beats, duration)

    def align_with_whisper(self, audio_path: str, lyrics_text: str) -> List[Dict]:
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_path, word_timestamps=True)

            whisper_lines = []
            for segment in segments:
                for word_info in segment.words:
                    whisper_lines.append({
                        "word": word_info.word,
                        "start": word_info.start,
                        "end": word_info.end,
                    })

            parsed_lyrics = self.parse_lyrics(lyrics_text)
            aligned = self._match_lyrics_to_whisper(parsed_lyrics, whisper_lines)
            return aligned

        except ImportError:
            parsed = self.parse_lyrics(lyrics_text)
            return parsed

    def save_alignment(self, alignment: List[Dict], output_path: str):
        output = {
            "lines": alignment,
            "total_lines": len(alignment),
        }
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

    def load_alignment(self, alignment_path: str) -> List[Dict]:
        with open(alignment_path, "r") as f:
            data = json.load(f)
        return data.get("lines", [])

    def _is_section_header(self, line: str) -> bool:
        line_lower = line.lower().strip()
        line_clean = re.sub(r'[^a-zA-Z\s]', '', line_lower)
        for marker in self.section_markers:
            if marker.lower() in line_clean:
                return True
        return False

    def _extract_section_name(self, line: str) -> str:
        line_clean = re.sub(r'[^a-zA-Z\s]', '', line)
        for marker in self.section_markers:
            if marker.lower() in line_clean.lower():
                return marker
        return line_clean.strip()

    def _clean_lyric_line(self, line: str) -> str:
        line = re.sub(r'\[.*?\]', '', line)
        line = re.sub(r'\(.*?\)', '', line)
        return line.strip()

    def _estimate_importance(self, text: str) -> float:
        importance = 0.5

        chorus_keywords = ["love", "baby", "heart", "soul", "forever", "always"]
        if any(kw in text.lower() for kw in chorus_keywords):
            importance += 0.2

        if len(text.split()) <= 5:
            importance += 0.1

        if text.isupper():
            importance += 0.1

        return min(importance, 1.0)

    def _evenly_distribute(self, lyrics: List[Dict], duration: float) -> List[Dict]:
        if not lyrics:
            return []

        time_per_line = duration / len(lyrics)
        aligned = []

        for i, line in enumerate(lyrics):
            start = i * time_per_line
            end = (i + 1) * time_per_line
            aligned.append({
                **line,
                "start": round(start, 3),
                "end": round(end, 3),
            })

        return aligned

    def _align_with_sections(self, lyrics: List[Dict], sections: List[Dict]) -> List[Dict]:
        aligned = []
        lyrics_per_section = self._distribute_lyrics_to_sections(lyrics, sections)

        for section, section_lyrics in zip(sections, lyrics_per_section):
            if not section_lyrics:
                continue

            section_duration = section["end"] - section["start"]
            time_per_line = section_duration / len(section_lyrics)

            for i, line in enumerate(section_lyrics):
                start = section["start"] + (i * time_per_line)
                end = section["start"] + ((i + 1) * time_per_line)
                aligned.append({
                    **line,
                    "start": round(start, 3),
                    "end": round(end, 3),
                })

        return aligned

    def _align_with_beats(self, lyrics: List[Dict], beats: List[float], duration: float) -> List[Dict]:
        if not beats:
            return self._evenly_distribute(lyrics, duration)

        beats_per_line = max(1, len(beats) // len(lyrics))
        aligned = []

        for i, line in enumerate(lyrics):
            beat_idx = i * beats_per_line
            if beat_idx >= len(beats):
                break

            start = beats[beat_idx]
            end_idx = min(beat_idx + beats_per_line, len(beats) - 1)
            end = beats[end_idx] if end_idx < len(beats) else start + 2.0

            aligned.append({
                **line,
                "start": round(start, 3),
                "end": round(end, 3),
            })

        return aligned

    def _distribute_lyrics_to_sections(self, lyrics: List[Dict], sections: List[Dict]) -> List[List[Dict]]:
        if not sections:
            return [lyrics]

        result = [[] for _ in sections]
        lyrics_per_section = len(lyrics) // len(sections)
        remainder = len(lyrics) % len(sections)

        idx = 0
        for i, section in enumerate(sections):
            count = lyrics_per_section + (1 if i < remainder else 0)
            result[i] = lyrics[idx:idx+count]
            idx += count

        return result

    def _match_lyrics_to_whisper(self, lyrics: List[Dict], whisper_words: List[Dict]) -> List[Dict]:
        if not whisper_words:
            return lyrics

        aligned = []
        whisper_idx = 0

        for line in lyrics:
            words = line["text"].split()
            if not words:
                continue

            matched_words = []
            for word in words:
                while whisper_idx < len(whisper_words):
                    whisper_word = whisper_words[whisper_idx]["word"].strip()
                    if self._words_match(word, whisper_word):
                        matched_words.append(whisper_words[whisper_idx])
                        whisper_idx += 1
                        break
                    whisper_idx += 1

            if matched_words:
                aligned.append({
                    **line,
                    "start": matched_words[0]["start"],
                    "end": matched_words[-1]["end"],
                })
            else:
                aligned.append(line)

        return aligned

    def _words_match(self, word1: str, word2: str) -> bool:
        w1 = re.sub(r'[^a-zA-Z0-9]', '', word1.lower())
        w2 = re.sub(r'[^a-zA-Z0-9]', '', word2.lower())
        return w1 == w2 or w1.startswith(w2) or w2.startswith(w1)
