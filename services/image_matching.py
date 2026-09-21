"""Image similarity using CLIP embeddings when photo paths exist on disk."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from threading import Lock
from typing import Any

from services.ml_runtime import image_embedding_model, use_mock_ml


class ImageMatcher:
    """Compare lost/found photos; returns None when either side has no readable images."""

    def __init__(self) -> None:
        self._cache: dict[str, Any] = {}
        self._lock = Lock()

    def compare(
        self, lost_images: Sequence[str], found_images: Sequence[str]
    ) -> float | None:
        lost_paths = [path for path in lost_images if Path(path).is_file()]
        found_paths = [path for path in found_images if Path(path).is_file()]
        if not lost_paths or not found_paths:
            return None
        if use_mock_ml():
            return 0.5

        try:
            lost_vectors = [self._embed(path) for path in lost_paths]
            found_vectors = [self._embed(path) for path in found_paths]
        except Exception:
            return None

        best = 0.0
        for left in lost_vectors:
            for right in found_vectors:
                best = max(best, float((left * right).sum()))
        return max(0.0, min(1.0, best))

    def _embed(self, image_path: str):
        with self._lock:
            cached = self._cache.get(image_path)
            if cached is not None:
                return cached

        from PIL import Image

        from utils.images import prepare_clip_image

        with Image.open(image_path) as image:
            rgb = prepare_clip_image(image)
            vector = image_embedding_model().encode(
                rgb,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )

        with self._lock:
            self._cache[image_path] = vector
        return vector
