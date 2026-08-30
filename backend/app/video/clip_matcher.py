import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CLIPMatcher:
    """CLIP-based zero-shot visual matching for lyrics-to-video alignment."""

    def __init__(self, model_name: str = "ViT-B-32", device: Optional[str] = None):
        self.model_name = model_name
        self.device = device or self._detect_device()
        self._model = None
        self._preprocess = None
        self._tokenizer = None
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
            import open_clip
            import torch

            logger.info("Loading CLIP model: %s on %s", self.model_name, self.device)
            self._model, _, self._preprocess = open_clip.create_model_and_transforms(
                self.model_name, pretrained="laion2b_s34b_b79k"
            )
            self._tokenizer = open_clip.get_tokenizer(self.model_name)
            self._model.to(self.device)
            self._model.eval()
            self._loaded = True
            logger.info("CLIP model loaded successfully")
        except ImportError:
            logger.warning("open_clip not installed. CLIP matching unavailable.")
            raise
        except Exception as e:
            logger.error("Failed to load CLIP model: %s", e)
            raise

    def encode_image(self, image: np.ndarray) -> Optional[np.ndarray]:
        """Encode a BGR numpy frame into a CLIP visual embedding."""
        self._load_model()

        import torch
        from PIL import Image

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb)
        image_input = self._preprocess(pil_image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            image_features = self._model.encode_image(image_input)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        return image_features.cpu().numpy().flatten()

    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """Encode a text string into a CLIP text embedding."""
        self._load_model()

        import torch

        text_input = self._tokenizer([text]).to(self.device)

        with torch.no_grad():
            text_features = self._model.encode_text(text_input)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        return text_features.cpu().numpy().flatten()

    def score_frame_lyric(self, frame: np.ndarray, lyric_text: str) -> float:
        """Compute CLIP similarity between a video frame and lyric text."""
        image_emb = self.encode_image(frame)
        text_emb = self.encode_text(lyric_text)
        if image_emb is None or text_emb is None:
            return 0.0
        similarity = float(np.dot(image_emb, text_emb))
        return max(0.0, similarity)

    def score_segment_lyric(
        self, video_path: str, start: float, end: float, lyric_text: str, num_samples: int = 3
    ) -> float:
        """Score how well a video segment matches a lyric by sampling keyframes."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return 0.0

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        duration = end - start
        if duration <= 0:
            cap.release()
            return 0.0

        interval = duration / max(1, num_samples)
        scores = []
        for i in range(num_samples):
            t = start + i * interval
            frame_num = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if ret:
                score = self.score_frame_lyric(frame, lyric_text)
                scores.append(score)

        cap.release()
        return float(np.mean(scores)) if scores else 0.0

    def encode_video_segments(
        self, video_path: str, segment_duration: float = 3.0
    ) -> List[Dict[str, Any]]:
        """Encode each segment of a video into CLIP embeddings."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_duration = frame_count / fps if fps > 0 else 0

        segments = []
        idx = 0
        while True:
            start_time = idx * segment_duration
            if start_time >= total_duration:
                break
            end_time = min(start_time + segment_duration, total_duration)
            mid_time = (start_time + end_time) / 2
            frame_num = int(mid_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()
            if not ret:
                break
            embedding = self.encode_image(frame)
            if embedding is not None:
                segments.append({
                    "start": round(start_time, 2),
                    "end": round(end_time, 2),
                    "clip_embedding": embedding.tolist(),
                })
            idx += 1

        cap.release()
        return segments


_matcher_instance: Optional[CLIPMatcher] = None


def get_clip_matcher() -> CLIPMatcher:
    """Get or create the singleton CLIP matcher instance."""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = CLIPMatcher()
    return _matcher_instance
