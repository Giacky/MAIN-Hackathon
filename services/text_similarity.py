"""Semantic text similarity using BGE embeddings, with a mock fallback."""

from __future__ import annotations

import re
from threading import Lock
from typing import Any

from services.ml_runtime import text_embedding_model, use_mock_ml

# BGE cosine on short item phrases is inflated (unrelated pairs often sit ~0.6–0.7).
TEXT_COSINE_OFFSET = 0.70

# When both sides resolve to the same item type, attributes (color, wireless,
# brand) must not crush the text score. Color-word conflicts take a small cut.
_TYPE_MATCH_TEXT_FLOOR = 0.72
_COLOR_CONFLICT_PENALTY = 0.12

_COLOR_WORDS = frozenset(
    {
        "black",
        "white",
        "blue",
        "red",
        "green",
        "brown",
        "yellow",
        "orange",
        "pink",
        "purple",
        "grey",
        "gray",
        "silver",
        "gold",
        "beige",
        "navy",
        "tan",
    }
)
_WORD_RE = re.compile(r"[a-z0-9]+")


def calibrate_text_cosine(cosine: float) -> float:
    """Stretch raw cosine so only clearly similar descriptions score high."""
    if cosine <= TEXT_COSINE_OFFSET:
        return 0.0
    return float(max(0.0, min(1.0, (cosine - TEXT_COSINE_OFFSET) / (1.0 - TEXT_COSINE_OFFSET))))


def color_words(text: str) -> frozenset[str]:
    tokens = set(_WORD_RE.findall(text.lower()))
    return frozenset(token for token in tokens if token in _COLOR_WORDS)


def colors_conflict(text_a: str, text_b: str) -> bool:
    """True when both sides name colors and the sets are disjoint."""
    left = color_words(text_a)
    right = color_words(text_b)
    if not left or not right:
        return False
    return left.isdisjoint(right)


def apply_type_match_text_floor(
    calibrated_score: float,
    left_type: str | None,
    right_type: str | None,
    text_a: str,
    text_b: str,
) -> float:
    """Floor the text score when types match so color/wireless/brand cannot sink it.

    Different types are left unchanged here; matching_engine hard-gates them.
    """
    score = float(max(0.0, min(1.0, calibrated_score)))
    if left_type is None or right_type is None or left_type != right_type:
        return score
    floor = _TYPE_MATCH_TEXT_FLOOR
    if colors_conflict(text_a, text_b):
        floor = max(0.0, floor - _COLOR_CONFLICT_PENALTY)
    return float(max(score, floor))


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
