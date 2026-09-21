"""Photo similarity: DINOv2 shortlist + LightGlue re-rank."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
import logging
from typing import Any

from services.ml_runtime import (
    dino_model,
    dino_processor,
    feature_device,
    feature_matcher_stack,
    rembg_session,
    use_mock_ml,
)

logger = logging.getLogger(__name__)

_SHORTLIST_SIZE = 5
_DINO_WEIGHT = 0.35
_GLUE_WEIGHT = 0.65
_MIN_INLIERS = 8
_INLIER_NORM = 40.0
_CROP_PAD = 0.08

VISION_UNAVAILABLE_ERROR = (
    "Photo matching unavailable (the DINOv2 / LightGlue models could not score these "
    "pictures). Description, location, and time were still used. Run "
    "`python scripts/setup_vision.py` in the project venv, then restart the API."
)


@dataclass(frozen=True, slots=True)
class ImageCompareResult:
    """score is None when photos are missing, not shortlisted, or scoring failed."""

    score: float | None
    error: str | None = None
    shortlisted: bool = False
    dino_score: float | None = None
    inliers: int | None = None
    inlier_ratio: float | None = None


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


class ImageMatcher:
    """Compare lost/found photos; returns None score when either side has no readable images."""

    def __init__(self) -> None:
        self._dino_cache: dict[str, Any] = {}
        self._crop_cache: dict[str, Any] = {}
        self._lock = Lock()

    def compare(
        self, lost_images: Sequence[str], found_images: Sequence[str]
    ) -> ImageCompareResult:
        results = self.score_candidates(lost_images, (("pair", found_images),))
        return results.get("pair", ImageCompareResult(score=None))

    def score_candidates(
        self,
        anchor_paths: Sequence[str],
        candidates: Sequence[tuple[str, Sequence[str]]],
    ) -> dict[str, ImageCompareResult]:
        """Score many found reports against one lost anchor.

        LightGlue runs only for the top-_SHORTLIST_SIZE DINOv2 pairs. Outside
        the shortlist, score is None so matching weights renormalize without a
        weak photo zeroing the rank. If the vision stack cannot load at all,
        every candidate with photos gets score None plus an image_error.
        """
        anchor_files = [path for path in anchor_paths if Path(path).is_file()]
        prepared: list[tuple[str, list[str]]] = []
        for candidate_id, paths in candidates:
            files = [path for path in paths if Path(path).is_file()]
            prepared.append((candidate_id, files))

        out: dict[str, ImageCompareResult] = {}
        if not anchor_files:
            for candidate_id, _ in prepared:
                out[candidate_id] = ImageCompareResult(score=None)
            return out

        if use_mock_ml():
            for candidate_id, files in prepared:
                out[candidate_id] = ImageCompareResult(
                    score=0.5 if files else None
                )
            return out

        try:
            return self._score_with_dino_lightglue(anchor_files, prepared)
        except Exception:
            logger.exception("DINOv2/LightGlue photo matching failed")
            for candidate_id, files in prepared:
                out[candidate_id] = ImageCompareResult(
                    score=None,
                    error=VISION_UNAVAILABLE_ERROR if files else None,
                )
            return out

    def _score_with_dino_lightglue(
        self,
        anchor_files: list[str],
        prepared: list[tuple[str, list[str]]],
    ) -> dict[str, ImageCompareResult]:
        import numpy as np

        out: dict[str, ImageCompareResult] = {}
        anchor_embeds = [(path, self._embed_dino(path)) for path in anchor_files]

        ranked: list[tuple[str, float, str, str]] = []
        for candidate_id, files in prepared:
            if not files:
                out[candidate_id] = ImageCompareResult(score=None)
                continue
            best = -1.0
            best_pair = (anchor_files[0], files[0])
            for found_path in files:
                found_vec = self._embed_dino(found_path)
                for anchor_path, anchor_vec in anchor_embeds:
                    cosine = float(np.dot(anchor_vec, found_vec))
                    if cosine > best:
                        best = cosine
                        best_pair = (anchor_path, found_path)
            ranked.append((candidate_id, best, best_pair[0], best_pair[1]))

        ranked.sort(key=lambda item: item[1], reverse=True)
        shortlisted_ids = {item[0] for item in ranked[:_SHORTLIST_SIZE]}

        for candidate_id, dino_cos, left_path, right_path in ranked:
            if candidate_id not in shortlisted_ids:
                out[candidate_id] = ImageCompareResult(
                    score=None,
                    shortlisted=False,
                    dino_score=float(dino_cos),
                )
                continue

            glue_score = 0.0
            inliers: int | None = None
            inlier_ratio: float | None = None
            error: str | None = None
            try:
                glue_score, inliers, inlier_ratio = self._lightglue_score(
                    left_path, right_path
                )
                score = _DINO_WEIGHT * _clamp01(dino_cos) + _GLUE_WEIGHT * glue_score
            except Exception:
                logger.exception(
                    "LightGlue failed for shortlisted pair %s; keeping DINOv2 term",
                    candidate_id,
                )
                score = _clamp01(dino_cos)
                error = (
                    "Feature matching failed on this pair; using visual similarity only. "
                    "Description, location, and time were still used."
                )

            out[candidate_id] = ImageCompareResult(
                score=_clamp01(score),
                error=error,
                shortlisted=True,
                dino_score=float(dino_cos),
                inliers=inliers,
                inlier_ratio=inlier_ratio,
            )
        return out

    def _foreground_crop(self, image_path: str):
        with self._lock:
            cached = self._crop_cache.get(image_path)
            if cached is not None:
                return cached.copy()

        from PIL import Image

        with Image.open(image_path) as image:
            from PIL import ImageOps

            rgb = ImageOps.exif_transpose(image).convert("RGB")

        cropped = rgb
        try:
            from rembg import remove

            rgba = remove(rgb, session=rembg_session())
            if rgba.mode != "RGBA":
                rgba = rgba.convert("RGBA")
            alpha = rgba.getchannel("A")
            bbox = alpha.getbbox()
            if bbox is not None:
                left, top, right, bottom = bbox
                width = right - left
                height = bottom - top
                if width >= 8 and height >= 8:
                    pad_x = int(round(width * _CROP_PAD))
                    pad_y = int(round(height * _CROP_PAD))
                    left = max(0, left - pad_x)
                    top = max(0, top - pad_y)
                    right = min(rgb.width, right + pad_x)
                    bottom = min(rgb.height, bottom + pad_y)
                    cropped = rgb.crop((left, top, right, bottom))
        except Exception:
            logger.info("Foreground crop unavailable for %s; using full frame", image_path)

        with self._lock:
            self._crop_cache[image_path] = cropped.copy()
        return cropped

    def _embed_dino(self, image_path: str):
        with self._lock:
            cached = self._dino_cache.get(image_path)
            if cached is not None:
                return cached

        import numpy as np
        import torch

        crop = self._foreground_crop(image_path)
        processor = dino_processor()
        model = dino_model()
        inputs = processor(images=crop, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            outputs = model(**inputs)
            cls = outputs.last_hidden_state[:, 0]
            cls = torch.nn.functional.normalize(cls, p=2, dim=-1)
            vector = cls.squeeze(0).detach().cpu().numpy().astype(np.float32)

        with self._lock:
            self._dino_cache[image_path] = vector
        return vector

    def _lightglue_score(
        self, left_path: str, right_path: str
    ) -> tuple[float, int, float]:
        import cv2
        import numpy as np
        import torch
        from torchvision.transforms.functional import to_tensor

        _features_name, extractor, matcher = feature_matcher_stack()
        del _features_name
        device = torch.device(feature_device())

        left_img = self._foreground_crop(left_path)
        right_img = self._foreground_crop(right_path)
        left_t = to_tensor(left_img).unsqueeze(0).to(device)
        right_t = to_tensor(right_img).unsqueeze(0).to(device)

        def _to_lg_dict(feature_batch, image_tensor: torch.Tensor) -> dict:
            """Adapt ALIKED/DISK list outputs into LightGlue's nested dict input."""
            feat = feature_batch[0] if isinstance(feature_batch, (list, tuple)) else feature_batch
            if isinstance(feat, dict):
                keypoints = feat["keypoints"]
                descriptors = feat["descriptors"]
            else:
                keypoints = feat.keypoints
                descriptors = feat.descriptors
            if keypoints.ndim == 2:
                keypoints = keypoints.unsqueeze(0)
            if descriptors.ndim == 2:
                descriptors = descriptors.unsqueeze(0)
            _, _, height, width = image_tensor.shape
            return {
                "keypoints": keypoints,
                "descriptors": descriptors,
                "image_size": torch.tensor(
                    [[width, height]], device=image_tensor.device, dtype=torch.float32
                ),
            }

        with torch.inference_mode():
            left_raw = extractor(left_t)
            right_raw = extractor(right_t)
            left_dict = _to_lg_dict(left_raw, left_t)
            right_dict = _to_lg_dict(right_raw, right_t)
            matches = matcher({"image0": left_dict, "image1": right_dict})

        kpts0 = left_dict["keypoints"][0].detach().cpu().numpy()
        kpts1 = right_dict["keypoints"][0].detach().cpu().numpy()
        matches0 = matches["matches0"]
        if isinstance(matches0, (list, tuple)):
            matches0 = matches0[0]
        matches0 = matches0.detach().cpu().numpy().reshape(-1)
        valid = matches0 >= 0
        pts0 = kpts0[valid]
        pts1 = kpts1[matches0[valid].astype(int)]

        pts0 = np.asarray(pts0, dtype=np.float32).reshape(-1, 2)
        pts1 = np.asarray(pts1, dtype=np.float32).reshape(-1, 2)
        total_matches = int(pts0.shape[0])
        if total_matches < _MIN_INLIERS:
            return 0.0, total_matches, 0.0

        matrix, mask = cv2.findFundamentalMat(
            pts0, pts1, method=cv2.FM_RANSAC, ransacReprojThreshold=3.0, confidence=0.99
        )
        del matrix
        if mask is None:
            inliers = 0
        else:
            inliers = int(mask.ravel().sum())
        inlier_ratio = float(inliers / total_matches) if total_matches else 0.0
        if inliers < _MIN_INLIERS:
            return 0.0, inliers, inlier_ratio
        glue_score = _clamp01(inliers / _INLIER_NORM) * inlier_ratio
        return float(glue_score), inliers, inlier_ratio
