import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    clip_id: str
    score: float
    reason: str


class SemanticSearch:
    def __init__(self):
        self.model = None
        self.model_name = "all-MiniLM-L6-v2"
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        except ImportError:
            self.model = None

    def generate_embedding(self, text: str) -> List[float]:
        if self.model is None:
            return self._fallback_embedding(text)
        embedding = self.model.encode(text)
        return embedding.tolist()

    def generate_clip_embeddings(self, clips: List[Dict]) -> List[Dict]:
        enhanced_clips = []
        for clip in clips:
            text = self._clip_to_text(clip)
            embedding = self.generate_embedding(text)
            enhanced_clips.append({
                **clip,
                "semantic_embedding": embedding,
            })
        return enhanced_clips

    def generate_segment_embeddings(self, clips: List[Dict]) -> List[Dict]:
        """Generate embeddings for each segment description within clips."""
        enhanced_clips = []
        for clip in clips:
            segment_embeddings = []
            for seg in clip.get("segment_descriptions", []):
                caption = seg.get("caption", "")
                if caption:
                    emb = self.generate_embedding(caption)
                    segment_embeddings.append({**seg, "embedding": emb})
                else:
                    segment_embeddings.append(seg)
            enhanced_clips.append({
                **clip,
                "segment_embeddings": segment_embeddings,
            })
        return enhanced_clips

    def generate_clip_visual_embeddings(self, clips: List[Dict], video_dir: str = "") -> List[Dict]:
        """Generate averaged per-clip CLIP visual embedding from existing segment embeddings.

        If segments already have 'clip_embedding' (from clip_analyzer), just average them.
        If not and video_dir is provided, encode frames directly.
        """
        enhanced_clips = []
        for clip in clips:
            segment_descs = clip.get("segment_descriptions", clip.get("segment_embeddings", []))
            clip_embs = []

            for seg in segment_descs:
                clip_emb = seg.get("clip_embedding")
                if clip_emb is not None:
                    clip_embs.append(clip_emb)

            # If no pre-computed embeddings, try encoding from video
            if not clip_embs and video_dir:
                try:
                    from app.video.clip_matcher import get_clip_matcher
                    matcher = get_clip_matcher()
                    filename = clip.get("filename", "")
                    video_path = str(Path(video_dir) / filename)
                    cap = __import__("cv2").VideoCapture(video_path)
                    if cap.isOpened():
                        fps = cap.get(__import__("cv2").CAP_PROP_FPS) or 30
                        for seg in segment_descs:
                            seg_start = seg.get("start", 0)
                            seg_end = seg.get("end", 0)
                            mid = (seg_start + seg_end) / 2
                            cap.set(__import__("cv2").CAP_PROP_POS_FRAMES, int(mid * fps))
                            ret, frame = cap.read()
                            if ret:
                                emb = matcher.encode_image(frame)
                                if emb is not None:
                                    clip_embs.append(emb.tolist())
                        cap.release()
                except Exception as e:
                    logger.debug("CLIP encoding failed for %s: %s", clip.get("clip_id"), e)

            # Average all segment CLIP embeddings into a single per-clip embedding
            avg_emb = None
            if clip_embs:
                arr = np.array([e if isinstance(e, list) else e.tolist() for e in clip_embs])
                avg_emb = np.mean(arr, axis=0)
                norm = np.linalg.norm(avg_emb)
                if norm > 0:
                    avg_emb = (avg_emb / norm).tolist()
                else:
                    avg_emb = avg_emb.tolist()

            enhanced_clips.append({
                **clip,
                "clip_visual_embedding": avg_emb,
            })
        return enhanced_clips

    def search_clips(self, query: str, clips: List[Dict], top_k: int = 5) -> List[SearchResult]:
        query_embedding = self.generate_embedding(query)

        scored_clips = []
        for clip in clips:
            clip_embedding = clip.get("semantic_embedding", [])
            clip_text = self._clip_to_text(clip)

            embedding_score = 0.0
            if clip_embedding:
                embedding_score = self._cosine_similarity(query_embedding, clip_embedding)

            text_score = self._text_similarity(query, clip_text)

            score = max(embedding_score, text_score)

            reason = self._generate_reason(query, clip, score)
            scored_clips.append(SearchResult(
                clip_id=clip.get("clip_id", "unknown"),
                score=round(score, 3),
                reason=reason,
            ))

        scored_clips.sort(key=lambda x: x.score, reverse=True)
        return scored_clips[:top_k]

    def search_for_lyrics(self, lyrics: List[Dict], clips: List[Dict], top_k_per_line: int = 3) -> Dict[str, List[SearchResult]]:
        results = {}
        for line in lyrics:
            query = line.get("text", "")
            if query:
                results[query] = self.search_clips(query, clips, top_k_per_line)
        return results

    def search_segments(self, query: str, clips: List[Dict], top_k: int = 10, video_dir: str = "") -> List[Dict]:
        """Find the best matching segment across all clips for a query.

        Uses weighted fusion of 3 signals:
        - semantic: sentence-transformer cosine similarity (30%)
        - text: Jaccard word overlap (15%)
        - clip_visual: CLIP dot product (55%)
        """
        query_embedding = self.generate_embedding(query)

        clip_text_emb = None
        try:
            from app.video.clip_matcher import get_clip_matcher
            matcher = get_clip_matcher()
            clip_text_emb = matcher.encode_text(query)
        except Exception:
            pass

        results = []
        for clip in clips:
            for seg in clip.get("segment_embeddings", clip.get("segment_descriptions", [])):
                caption = seg.get("caption", "")
                if not caption:
                    continue

                seg_embedding = seg.get("embedding")
                emb_score = self._cosine_similarity(query_embedding, seg_embedding) if seg_embedding else 0.0
                text_score = self._text_similarity(query, caption)

                clip_vis_emb = seg.get("clip_embedding")
                clip_score = 0.0
                if clip_text_emb is not None and clip_vis_emb is not None:
                    clip_score = float(np.dot(np.array(clip_text_emb), np.array(clip_vis_emb)))
                    clip_score = max(0.0, clip_score)

                score = (
                    0.30 * emb_score +
                    0.15 * text_score +
                    0.55 * clip_score
                )
                if score > 0.05:
                    results.append({
                        "clip_id": clip.get("clip_id", "unknown"),
                        "segment_start": seg.get("start", 0),
                        "segment_end": seg.get("end", 0),
                        "caption": caption,
                        "score": round(score, 3),
                        "scores": {
                            "semantic": round(emb_score, 3),
                            "text": round(text_score, 3),
                            "clip_visual": round(clip_score, 3),
                        },
                    })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def search_clips_for_lyrics(self, lyrics: List[Dict], clips: List[Dict], top_k_per_line: int = 5) -> Dict[str, List[Dict]]:
        """Match each lyric line to the best WHOLE CLIP using 3-signal fusion.

        Signals:
        - semantic: sentence-transformer cosine similarity on full clip text (30%)
        - text: Jaccard word overlap between lyric and scene_description (15%)
        - clip_visual: CLIP dot product between lyric text embedding and averaged per-clip visual embedding (55%)
        """
        results = {}
        for line in lyrics:
            query = line.get("text", "")
            if query:
                results[query] = self._search_clips_single(query, clips, top_k_per_line)
        return results

    def _search_clips_single(self, query: str, clips: List[Dict], top_k: int = 5) -> List[Dict]:
        """Find the best matching WHOLE CLIP for a query string."""
        query_embedding = self.generate_embedding(query)

        # Encode query with CLIP text encoder
        clip_text_emb = None
        try:
            from app.video.clip_matcher import get_clip_matcher
            matcher = get_clip_matcher()
            clip_text_emb = matcher.encode_text(query)
        except Exception:
            pass

        results = []
        for clip in clips:
            # Signal 1: semantic embedding (sentence-transformer on full clip text)
            clip_semantic_emb = clip.get("semantic_embedding", [])
            emb_score = self._cosine_similarity(query_embedding, clip_semantic_emb) if clip_semantic_emb else 0.0

            # Signal 2: text overlap between lyric and scene description
            scene_desc = clip.get("scene_description", "")
            caption_text = " ".join(
                seg.get("caption", "") for seg in clip.get("segment_descriptions", [])
            )
            clip_text = f"{scene_desc} {caption_text}".strip()
            text_score = self._text_similarity(query, clip_text) if clip_text else 0.0

            # Signal 3: CLIP visual embedding (averaged across all segment frames)
            clip_vis_emb = clip.get("clip_visual_embedding")
            clip_score = 0.0
            if clip_text_emb is not None and clip_vis_emb is not None:
                clip_score = float(np.dot(np.array(clip_text_emb), np.array(clip_vis_emb)))
                clip_score = max(0.0, clip_score)

            score = (
                0.10 * emb_score +
                0.05 * text_score +
                0.85 * clip_score
            )

            if score > 0.01:
                results.append({
                    "clip_id": clip.get("clip_id", "unknown"),
                    "score": round(score, 3),
                    "scores": {
                        "semantic": round(emb_score, 3),
                        "text": round(text_score, 3),
                        "clip_visual": round(clip_score, 3),
                    },
                    "scene_description": scene_desc[:80],
                    "duration": clip.get("duration", 0),
                })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def search_segments_for_lyrics(self, lyrics: List[Dict], clips: List[Dict], top_k_per_line: int = 10, video_dir: str = "") -> Dict[str, List[Dict]]:
        """Match each lyric line to the best segment across all clips."""
        results = {}
        for line in lyrics:
            query = line.get("text", "")
            if query:
                results[query] = self.search_segments(query, clips, top_k_per_line, video_dir)
        return results

    def save_embeddings(self, clips: List[Dict], output_path: str):
        output = {
            "total_clips": len(clips),
            "clips": clips,
        }
        with open(output_path, "w") as f:
            json.dump(output, f, indent=2)

    def load_embeddings(self, embeddings_path: str) -> List[Dict]:
        with open(embeddings_path, "r") as f:
            data = json.load(f)
        return data.get("clips", [])

    def _clip_to_text(self, clip: Dict) -> str:
        parts = []
        if clip.get("scene_description"):
            parts.append(clip["scene_description"])
        for seg in clip.get("segment_descriptions", []):
            caption = seg.get("caption", "")
            if caption:
                parts.append(caption)
        if clip.get("actions"):
            parts.append(" ".join(clip["actions"]))
        if clip.get("objects"):
            parts.append(" ".join(clip["objects"]))
        if clip.get("emotion"):
            parts.append(clip["emotion"])
        return " ".join(parts) if parts else "video clip"

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(dot_product / (norm1 * norm2))

    def _text_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)

    def _fallback_embedding(self, text: str) -> List[float]:
        import hashlib
        words = text.lower().split()
        embedding = [0.0] * 384
        for word in words:
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % 384
            embedding[idx] = 1.0
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = (np.array(embedding) / norm).tolist()
        return embedding

    def _generate_reason(self, query: str, clip: Dict, score: float) -> str:
        if score > 0.8:
            return f"Strong semantic match with query"
        elif score > 0.6:
            return f"Good semantic match"
        elif score > 0.4:
            return f"Moderate semantic match"
        else:
            return f"Weak semantic match"
