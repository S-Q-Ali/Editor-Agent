import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import numpy as np


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
