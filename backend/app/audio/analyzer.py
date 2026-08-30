import json
import subprocess
import numpy as np
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


class MusicAnalyzer:
    def __init__(self):
        self.supported_formats = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']

    def analyze(self, audio_path: str) -> Dict[str, Any]:
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported audio format: {path.suffix}")

        if LIBROSA_AVAILABLE:
            return self._analyze_with_librosa(audio_path)
        else:
            return self._analyze_with_ffprobe(audio_path)

    def _analyze_with_librosa(self, audio_path: str) -> Dict[str, Any]:
        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)

        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        if hasattr(tempo, '__len__'):
            bpm = float(tempo[0]) if len(tempo) > 0 else 0.0
        else:
            bpm = float(tempo)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        times = librosa.times_like(onset_env, sr=sr)

        hop_length = 512
        stft = np.abs(librosa.stft(y, hop_length=hop_length))
        rms = librosa.feature.rms(S=stft)[0]
        energy_times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=hop_length)
        energy_curve = list(zip(energy_times.tolist(), rms.tolist()))

        intervals = librosa.util.frame(y, frame_length=2048, hop_length=hop_length)
        silence_threshold = 0.01
        is_silent = np.mean(np.abs(intervals), axis=0) < silence_threshold
        silence_regions = self._find_silence_regions(is_silent, sr, hop_length)

        segments = self._detect_sections(y, sr, onset_env)

        downbeats = self._detect_downbeats(y, sr, beat_frames)

        return {
            "duration": round(duration, 2),
            "bpm": round(bpm, 1),
            "beats": [round(t, 3) for t in beat_times],
            "downbeats": [round(t, 3) for t in downbeats],
            "sections": segments,
            "energy_curve": [[round(t, 3), round(float(e), 4)] for t, e in energy_curve[:100]],
            "silence_regions": silence_regions,
            "sample_rate": sr,
        }

    def _analyze_with_ffprobe(self, audio_path: str) -> Dict[str, Any]:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr}")

        data = json.loads(result.stdout)
        duration = float(data.get("format", {}).get("duration", 0))

        return {
            "duration": round(duration, 2),
            "bpm": 0,
            "beats": [],
            "downbeats": [],
            "sections": [],
            "energy_curve": [],
            "silence_regions": [],
            "sample_rate": 0,
            "note": "Limited analysis - install librosa for full analysis",
        }

    def _find_silence_regions(self, is_silent: np.ndarray, sr: int, hop_length: int) -> list:
        regions = []
        in_silence = False
        start = 0

        for i, silent in enumerate(is_silent):
            if silent and not in_silence:
                in_silence = True
                start = i
            elif not silent and in_silence:
                in_silence = False
                regions.append({
                    "start": round(start * hop_length / sr, 3),
                    "end": round(i * hop_length / sr, 3),
                })

        return regions

    def _detect_sections(self, y: np.ndarray, sr: int, onset_env: np.ndarray) -> list:
        try:
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
            bound_frames = librosa.segment.agglomerative(mfcc, 6)
            bound_times = librosa.frames_to_time(bound_frames, sr=sr).tolist()

            sections = []
            labels = ["Intro", "Verse 1", "Chorus", "Verse 2", "Chorus 2", "Bridge", "Outro"]
            for i in range(len(bound_times) - 1):
                label = labels[i] if i < len(labels) else f"Section {i+1}"
                sections.append({
                    "start": round(bound_times[i], 3),
                    "end": round(bound_times[i+1], 3),
                    "label": label,
                })
            return sections
        except Exception:
            return []

    def _detect_downbeats(self, y: np.ndarray, sr: int, beat_frames: np.ndarray) -> list:
        try:
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            if hasattr(tempo, '__len__'):
                bpm_val = float(tempo[0]) if len(tempo) > 0 else 120.0
            else:
                bpm_val = float(tempo)

            downbeat_interval = max(1, int(round(60 * sr / (bpm_val * 512))))
            downbeat_frames = beat_frames[::downbeat_interval] if len(beat_frames) > 0 else np.array([])
            downbeat_times = librosa.frames_to_time(downbeat_frames, sr=sr)
            return [round(t, 3) for t in downbeat_times.tolist()]
        except Exception:
            return []

    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"FFprobe failed: {result.stderr}")
        return json.loads(result.stdout)
