import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

BLIP2_MODEL = "Salesforce/blip-image-captioning-base"


class FrameCaptioner:
    """BLIP-based frame captioning for video segments."""

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
            from transformers import BlipProcessor, BlipForConditionalGeneration
            import torch

            logger.info("Loading BLIP model: %s on %s", self.model_name, self.device)
            self._processor = BlipProcessor.from_pretrained(self.model_name)
            self._model = BlipForConditionalGeneration.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map=self.device if self.device == "cuda" else None,
            )
            self._loaded = True
            logger.info("BLIP model loaded successfully")
        except ImportError:
            logger.warning("transformers/torch not installed. Frame captioning unavailable.")
            raise
        except Exception as e:
            logger.error("Failed to load BLIP model: %s", e)
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
        """Generate a text caption for a single frame using BLIP."""
        self._load_model()

        from PIL import Image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        inputs = self._processor(images=image, return_tensors="pt")
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        output = self._model.generate(**inputs, max_new_tokens=30, num_beams=3)
        caption = self._processor.decode(output[0], skip_special_tokens=True).strip()
        caption = self._clean_caption(caption)
        return caption

    def caption_frame_with_prompt(self, frame: np.ndarray, prompt: str) -> str:
        """Generate a caption conditioned on a text prompt.

        The model generates a caption that continues the prompt, conditioned on the image.
        Example: prompt="a photo of someone opening their eyes" →
                 output="a child opening their eyes in bed"
        """
        self._load_model()

        from PIL import Image
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)

        text = f"a photo of {prompt}"
        inputs = self._processor(images=image, text=text, return_tensors="pt")
        if self.device == "cuda":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        output = self._model.generate(**inputs, max_new_tokens=30, num_beams=3)
        caption = self._processor.decode(output[0], skip_special_tokens=True).strip()
        caption = self._clean_caption(caption)
        return caption

    def score_lyric_visual_match(
        self, frame: np.ndarray, lyric_text: str, clip_score: float = 0.0
    ) -> float:
        """Score how well a frame matches a lyric using conditioned BLIP.

        Generates a caption anchored to the lyric and measures similarity.
        Returns a score between 0 and 1.
        """
        try:
            prompt = self._lyric_to_prompt(lyric_text)
            conditioned = self.caption_frame_with_prompt(frame, prompt)
            lyric_words = set(lyric_text.lower().split())
            caption_words = set(conditioned.lower().split())
            if not lyric_words or not caption_words:
                return 0.0
            intersection = lyric_words & caption_words
            union = lyric_words | caption_words
            text_sim = len(intersection) / len(union) if union else 0.0
            conditioned_score = min(1.0, text_sim * 2)
            return max(conditioned_score, clip_score)
        except Exception as e:
            logger.warning("Conditioned BLIP scoring failed: %s", e)
            return clip_score

    @staticmethod
    def _lyric_to_prompt(lyric_text: str) -> str:
        """Convert a lyric line to a BLIP prompt for conditioned captioning."""
        lyric_lower = lyric_text.lower().strip()

        verb_prompts = {
            "open": "a photo of someone opening their eyes",
            "eyes": "a photo of someone opening their eyes",
            "wake": "a photo of someone waking up",
            "jump": "a photo of someone jumping",
            "stretch": "a photo of someone stretching their arms",
            "dance": "a photo of someone dancing",
            "clap": "a photo of someone clapping hands",
            "brush": "a photo of someone brushing teeth",
            "teeth": "a photo of someone brushing teeth",
            "wash": "a photo of someone washing hands or face",
            "splash": "a photo of someone splashing water",
            "smile": "a photo of someone smiling",
            "sing": "a photo of someone singing",
            "run": "a photo of someone running",
            "walk": "a photo of someone walking",
            "sit": "a photo of someone sitting",
            "stand": "a photo of someone standing",
            "lay": "a photo of someone lying down",
            "sleep": "a photo of someone sleeping",
            "eat": "a photo of someone eating food",
            "drink": "a photo of someone drinking",
            "read": "a photo of someone reading a book",
            "play": "a photo of someone playing",
            "touch": "a photo of someone touching something",
            "wiggle": "a photo of someone wiggling",
            "shine": "a photo of something shining bright",
            "bright": "a photo of something bright and colorful",
            "sun": "a photo of the sun or sunshine",
            "morning": "a photo of a morning scene",
            "hello": "a photo of someone saying hello",
            "goodbye": "a photo of someone waving goodbye",
            "happy": "a photo of a happy child",
            "ready": "a photo of someone getting ready",
        }

        for keyword, prompt in verb_prompts.items():
            if keyword in lyric_lower:
                return prompt

        return f"a photo of {lyric_text}"

    @staticmethod
    def _clean_caption(caption: str) -> str:
        """Remove repetitive phrases from generated captions."""
        words = caption.split()
        if len(words) < 3:
            return caption
        for pattern_len in range(1, len(words) // 2 + 1):
            for start in range(len(words) - pattern_len * 2 + 1):
                pattern = words[start:start + pattern_len]
                repeated = True
                for j in range(start + pattern_len, start + pattern_len * 2):
                    if j >= len(words) or words[j] != pattern[(j - start) % pattern_len]:
                        repeated = False
                        break
                if repeated:
                    return " ".join(words[:start + pattern_len])
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
