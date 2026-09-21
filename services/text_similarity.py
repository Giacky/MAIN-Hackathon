"""Semantic text similarity using BGE embeddings, with a mock fallback."""

from __future__ import annotations

from threading import Lock
from typing import Any

from services.ml_runtime import text_embedding_model, use_mock_ml

# BGE cosine on short item phrases is inflated (unrelated pairs often sit ~0.6–0.7).
TEXT_COSINE_OFFSET = 0.70


def calibrate_text_cosine(cosine: float) -> float:
    """Stretch raw cosine so only clearly similar descriptions score high."""
    if cosine <= TEXT_COSINE_OFFSET:
        return 0.0
    return float(max(0.0, min(1.0, (cosine - TEXT_COSINE_OFFSET) / (1.0 - TEXT_COSINE_OFFSET))))


class TextSimilarityService:
    """Compare two descriptions; sentence embeddings replace the mock at runtime."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._lock = Lock()

    def compare(self, text_a: str, text_b: str) -> float:
        left = text_a.strip()
        right = text_b.strip()
        if not left or not right:
            return 0.0
        if use_mock_ml():
            return 0.5
        try:
            vector_a = self._embed(left)
            vector_b = self._embed(right)
        except Exception:
            return 0.5
        score = calibrate_text_cosine(float((vector_a * vector_b).sum()))
        return max(0.0, min(1.0, score))

    def _embed(self, text: str):
        with self._lock:
            cached = self._cache.get(text)
            if cached is not None:
                return cached
        vector = text_embedding_model().encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        with self._lock:
            self._cache[text] = vector
        return vector
