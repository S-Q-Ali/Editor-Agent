import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np


class ClipAnalyzer:
    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm']

    def analyze_clip(self, video_path: str) -> Dict[str, Any]:
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported video format: {path.suffix}")

        video_info = self._get_video_info(video_path)
        visual_features = self._extract_visual_features(video_path)
        quality_metrics = self._assess_quality(video_path)
        best_segments = self._find_best_segments(video_path)

        return {
            "clip_id": path.stem,
            "filename": path.name,
            "duration": video_info.get("duration", 0),
            "width": video_info.get("width", 0),
            "height": video_info.get("height", 0),
            "fps": video_info.get("fps", 0),
            "codec": video_info.get("codec", "unknown"),
            "actions": visual_features.get("actions", []),
            "objects": visual_features.get("objects", []),
            "emotion": visual_features.get("emotion", "neutral"),
            "motion_score": visual_features.get("motion_score", 0),
            "scene_description": visual_features.get("description", ""),
            "quality_score": quality_metrics.get("quality_score", 0),
            "brightness": quality_metrics.get("brightness", 0),
            "sharpness": quality_metrics.get("sharpness", 0),
            "contrast": quality_metrics.get("contrast", 0),
            "best_segments": best_segments,
        }

    def analyze_all_clips(self, clips_dir: str) -> List[Dict]:
        clips_path = Path(clips_dir)
        if not clips_path.exists():
            raise FileNotFoundError(f"Clips directory not found: {clips_dir}")

        clips = []
        for ext in self.supported_formats:
            for video_file in clips_path.glob(f"*{ext}"):
                try:
                    analysis = self.analyze_clip(str(video_file))
                    clips.append(analysis)
                except Exception as e:
                    print(f"Failed to analyze {video_file}: {e}")

        return clips

    def save_clip_index(self, clips: List[Dict], output_path: str):
        output = {
            "total_clips": len(clips),
            "clips": clips,
        }
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

    def _get_video_info(self, video_path: str) -> Dict[str, Any]:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return {"error": result.stderr}

        data = json.loads(result.stdout)

        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if not video_stream:
            return {"error": "No video stream found"}

        duration = float(data.get("format", {}).get("duration", 0))
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))

        fps_str = video_stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)

        return {
            "duration": round(duration, 2),
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "codec": video_stream.get("codec_name", "unknown"),
        }

    def _extract_visual_features(self, video_path: str) -> Dict[str, Any]:
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return self._default_visual_features()

            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            sample_interval = max(1, frame_count // 10)

            motion_scores = []
            brightness_values = []
            sample_count = 0

            prev_frame = None
            for i in range(0, frame_count, sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness_values.append(np.mean(gray))

                if prev_frame is not None:
                    diff = cv2.absdiff(prev_frame, gray)
                    motion_scores.append(np.mean(diff) / 255.0)

                prev_frame = gray
                sample_count += 1

            cap.release()

            avg_motion = np.mean(motion_scores) if motion_scores else 0
            avg_brightness = np.mean(brightness_values) if brightness_values else 128

            emotion = self._classify_emotion(avg_brightness, avg_motion)

            return {
                "motion_score": round(float(avg_motion), 3),
                "emotion": emotion,
                "brightness": round(float(avg_brightness), 1),
                "actions": self._infer_actions(avg_motion),
                "objects": [],
                "description": f"Video with {'high' if avg_motion > 0.3 else 'low'} motion, {'bright' if avg_brightness > 140 else 'dark'} scene",
            }

        except Exception as e:
            return self._default_visual_features()

    def _assess_quality(self, video_path: str) -> Dict[str, float]:
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"quality_score": 0}

            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            cap.release()

            if not ret:
                return {"quality_score": 0}

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            brightness = np.mean(gray)
            contrast = np.std(gray)
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

            brightness_score = 1.0 - abs(brightness - 128) / 128
            contrast_score = min(contrast / 64, 1.0)
            sharpness_score = min(sharpness / 500, 1.0)

            quality_score = (
                brightness_score * 0.3 +
                contrast_score * 0.3 +
                sharpness_score * 0.4
            )

            return {
                "quality_score": round(float(quality_score), 3),
                "brightness": round(float(brightness), 1),
                "sharpness": round(float(sharpness), 1),
                "contrast": round(float(contrast), 1),
            }

        except Exception:
            return {"quality_score": 0, "brightness": 0, "sharpness": 0, "contrast": 0}

    def _find_best_segments(self, video_path: str, segment_duration: float = 3.0) -> List[Dict]:
        try:
            info = self._get_video_info(video_path)
            duration = info.get("duration", 0)
            if duration <= 0:
                return []

            num_segments = max(1, int(duration / segment_duration))
            segments = []

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return []

            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frames_per_segment = int(segment_duration * fps)

            for i in range(num_segments):
                start_time = i * segment_duration
                start_frame = int(start_time * fps)

                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                brightness = np.mean(gray)

                score = min(sharpness / 500, 1.0) * 0.5 + (1.0 - abs(brightness - 128) / 128) * 0.5

                segments.append({
                    "start": round(start_time, 2),
                    "end": round(min(start_time + segment_duration, duration), 2),
                    "score": round(float(score), 3),
                })

            cap.release()

            segments.sort(key=lambda x: x["score"], reverse=True)
            return segments[:5]

        except Exception:
            return []

    def _classify_emotion(self, brightness: float, motion: float) -> str:
        if brightness > 160 and motion > 0.3:
            return "happy"
        elif brightness < 80:
            return "sad"
        elif motion > 0.4:
            return "excited"
        elif motion < 0.1:
            return "calm"
        else:
            return "neutral"

    def _infer_actions(self, motion_score: float) -> List[str]:
        if motion_score > 0.4:
            return ["active", "moving"]
        elif motion_score > 0.2:
            return ["moderate movement"]
        else:
            return ["still", "static"]

    def _default_visual_features(self) -> Dict[str, Any]:
        return {
            "motion_score": 0,
            "emotion": "neutral",
            "brightness": 128,
            "actions": [],
            "objects": [],
            "description": "Unable to analyze visual features",
        }
