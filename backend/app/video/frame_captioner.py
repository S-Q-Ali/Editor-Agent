import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

BLIP2_MODEL = "Salesforce/blip2-opt-2.7b"


class FrameCaptioner:
    """BLIP-2 based frame captioning for video segments."""

    def __init__(self, model_name: str = BLIP2_MODEL, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or self._detect_device()
        self._processor = None
        self._model = None
        self._loaded = False

    def _detect_device(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def _load_model(self):
        if self._loaded:
            return
        try:
            from transformers import Blip2Processor, Blip2ForConditionalGeneration
            import torch

            logger.info("Loading BLIP-2 model: %s on %s", self.model_name, self.device)
            self._processor = Blip2Processor.from_pretrained(self.model_name)
            self._model = Blip2ForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device if self.device == "cuda" else None,
            )
            self._loaded = True
            logger.info("BLIP-2 model loaded successfully")
        except ImportError:
            logger.warning("transformers/torch not installed. Frame captioning unavailable.")
            raise
        except Exception as e:
            logger.error("Failed to load BLIP-2 model: %s", e)
            raise

    def caption_video(self, video_path: str, interval: float = 2.0) -> List[Dict[str, Any]]:
        """Extract keyframes and generate captions for each segment.

        Returns list of dicts with keys: start, end, caption
        """
        raw_frames = self._extract_frames(video_path, interval)
        if not raw_frames:
            return []

        raw_captions = []
        for timestamp, frame in raw_frames:
            caption = self._caption_frame(frame)
            raw_captions.append({
                "start": round(timestamp, 2),
                "end": round(timestamp + interval, 2),
                "caption": caption,
            })

        merged = self._merge_captions(raw_captions)
        return merged

    def _extract_frames(self, video_path: str, interval: float) -> List[Tuple[float, np.ndarray]]:
        """Extract frames from video at given interval."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("Cannot open video: %s", video_path)
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_interval = max(1, int(fps * interval))
        frames = []
        idx = 0

        while True:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                break
            timestamp = idx / fps
            frames.append((timestamp, frame))
            idx += frame_interval

        cap.release()
        return frames

    def _caption_frame(self, frame: np.ndarray) -> str:
        """Generate a text caption for a single frame using BLIP-2."""
        self._load_model()

        from PIL import Image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        inputs = self._processor(images=image, return_tensors="pt")
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        output = self._model.generate(**inputs, max_new_tokens=50)
        caption = self._processor.decode(output[0], skip_special_tokens=True).strip()
        return caption

    def _merge_captions(self, raw_captions: List[Dict[str, Any]], similarity_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Merge adjacent captions with similar text into longer segments."""
        if not raw_captions:
            return []

        merged = [raw_captions[0].copy()]
        for item in raw_captions[1:]:
            prev = merged[-1]
            if self._captions_similar(prev["caption"], item["caption"], similarity_threshold):
                prev["end"] = item["end"]
                prev["caption"] = self._pick_better_caption(prev["caption"], item["caption"])
            else:
                merged.append(item.copy())
        return merged

    @staticmethod
    def _captions_similar(a: str, b: str, threshold: float) -> bool:
        """Check if two captions are similar enough to merge."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return False
        intersection = words_a & words_b
        union = words_a | words_b
        jaccard = len(intersection) / len(union)
        return jaccard >= threshold

    @staticmethod
    def _pick_better_caption(a: str, b: str) -> str:
        """Pick the more descriptive caption (longer with more detail)."""
        return a if len(a) >= len(b) else b


_captioner_instance: Optional[FrameCaptioner] = None


def get_captioner() -> FrameCaptioner:
    """Get or create the singleton captioner instance."""
    global _captioner_instance
    if _captioner_instance is None:
        _captioner_instance = FrameCaptioner()
    return _captioner_instance
