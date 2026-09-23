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
    sift_matcher_stack,
    use_mock_ml,
)

logger = logging.getLogger(__name__)

_SHORTLIST_SIZE = 5
_DINO_WEIGHT = 0.35
_GLUE_WEIGHT = 0.65
_MIN_INLIERS = 4
_INLIER_NORM = 40.0
_CROP_PAD = 0.08
# Seeded AirPods pair sits ~0.47 DINOv2; wallet vs AirPods ~0.07. Floor the band
# in the gap so geometry misses still count as the same object when DINO agrees.
_SAME_OBJECT_DINO_MIN = 0.35
_TINY_MASK_AREA_FRAC = 0.02
_ROTATION_ANGLES = (0, 90, 180, 270)
_ROTATION_EARLY_STOP = 20

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
    same_object: bool | None = None


def _clamp01(value: float) -> float:
    return float(max(0.0, min(1.0, value)))


def same_object_decision(dino_cos: float, inliers: int | None) -> bool:
    """True when LightGlue locks (>=4 inliers) or DINOv2 is in the same-object band."""
    if inliers is not None and int(inliers) >= _MIN_INLIERS:
        return True
    return _clamp01(float(dino_cos)) >= _SAME_OBJECT_DINO_MIN


def blend_photo_score(dino_cos: float, glue_score: float) -> float:
    """Combine DINOv2 cosine with LightGlue geometry.

    Keep the 0.35/0.65 blend only when LightGlue found a geometric model.
    On a miss (glue_score == 0), return the clamped DINO cosine so a geometry
    miss does not zero 65% of the photo score.
    """
    dino = _clamp01(float(dino_cos))
    glue = _clamp01(float(glue_score))
    if glue <= 0.0:
        return dino
    return _clamp01(_DINO_WEIGHT * dino + _GLUE_WEIGHT * glue)


def count_geometric_inliers(pts0: Any, pts1: Any) -> int:
    """Homography RANSAC first (~3px), then fundamental matrix if inliers are low."""
    import cv2
    import numpy as np

    src = np.asarray(pts0, dtype=np.float32).reshape(-1, 2)
    dst = np.asarray(pts1, dtype=np.float32).reshape(-1, 2)
    total = int(src.shape[0])
    if total < 4:
        return 0

    homography_inliers = _ransac_inlier_count(
        cv2.findHomography(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3.0)
    )
    if homography_inliers >= _MIN_INLIERS:
        return homography_inliers

    fundamental_inliers = 0
    if total >= 8:
        fundamental_inliers = _ransac_inlier_count(
            cv2.findFundamentalMat(
                src,
                dst,
                method=cv2.FM_RANSAC,
                ransacReprojThreshold=3.0,
                confidence=0.99,
            )
        )
        if fundamental_inliers >= _MIN_INLIERS:
            return fundamental_inliers
    return max(homography_inliers, fundamental_inliers)


def _ransac_inlier_count(cv_result: Any) -> int:
    if cv_result is None:
        return 0
    if not isinstance(cv_result, (tuple, list)) or len(cv_result) < 2:
        return 0
    mask = cv_result[1]
    if mask is None:
        return 0
    return int(mask.ravel().sum())


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
        out: dict[str, ImageCompareResult] = {}
        anchor_embeds = [
            (path, self._embed_dino_variants(path)) for path in anchor_files
        ]

        ranked: list[tuple[str, float, str, str]] = []
        for candidate_id, files in prepared:
            if not files:
                out[candidate_id] = ImageCompareResult(score=None)
                continue
            best = -1.0
            best_pair = (anchor_files[0], files[0])
            for found_path in files:
                found_vecs = self._embed_dino_variants(found_path)
                for anchor_path, anchor_vecs in anchor_embeds:
                    cosine = _max_cosine(anchor_vecs, found_vecs)
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
                    same_object=None,
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
                score = blend_photo_score(dino_cos, glue_score)
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
                same_object=same_object_decision(dino_cos, inliers),
            )
        return out

    def _foreground_crop(self, image_path: str):
        crop, _tiny = self._foreground_crop_with_meta(image_path)
        return crop

    def _foreground_crop_with_meta(self, image_path: str) -> tuple[Any, bool]:
        with self._lock:
            cached = self._crop_cache.get(image_path)
            if cached is not None:
                crop, tiny = cached
                return crop.copy(), tiny

        from PIL import Image

        with Image.open(image_path) as image:
            from PIL import ImageOps

            rgb = ImageOps.exif_transpose(image).convert("RGB")

        cropped = rgb
        tiny_mask = False
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
                    mask_area = float(width * height)
                    frame_area = float(max(1, rgb.width * rgb.height))
                    tiny_mask = (mask_area / frame_area) < _TINY_MASK_AREA_FRAC
                else:
                    tiny_mask = True
            else:
                tiny_mask = True
        except Exception:
            logger.info("Foreground crop unavailable for %s; using full frame", image_path)

        with self._lock:
            self._crop_cache[image_path] = (cropped.copy(), tiny_mask)
        return cropped, tiny_mask

    def _center_crop(self, image_path: str):
        from PIL import Image
        from PIL import ImageOps

        with Image.open(image_path) as image:
            rgb = ImageOps.exif_transpose(image).convert("RGB")
        width, height = rgb.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        return rgb.crop((left, top, left + side, top + side))

    def _embed_dino_variants(self, image_path: str) -> list[Any]:
        with self._lock:
            cached = self._dino_cache.get(image_path)
            if cached is not None:
                return list(cached)

        crop, tiny = self._foreground_crop_with_meta(image_path)
        vectors = [self._embed_pil(crop)]
        if tiny:
            center = self._center_crop(image_path)
            vectors.append(self._embed_pil(center))

        with self._lock:
            self._dino_cache[image_path] = tuple(vectors)
        return vectors

    def _embed_dino(self, image_path: str):
        return self._embed_dino_variants(image_path)[0]

    def _embed_pil(self, crop: Any):
        import numpy as np
        import torch

        processor = dino_processor()
        model = dino_model()
        inputs = processor(images=crop, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            outputs = model(**inputs)
            cls = outputs.last_hidden_state[:, 0]
            cls = torch.nn.functional.normalize(cls, p=2, dim=-1)
            return cls.squeeze(0).detach().cpu().numpy().astype(np.float32)

    def _lightglue_score(
        self, left_path: str, right_path: str
    ) -> tuple[float, int, float]:
        _features_name, extractor, matcher = feature_matcher_stack()
        del _features_name

        left_img = self._foreground_crop(left_path)
        right_img = self._foreground_crop(right_path)
        glue_score, inliers, inlier_ratio = self._match_with_rotations(
            extractor, matcher, left_img, right_img
        )
        if glue_score > 0.0:
            return glue_score, inliers, inlier_ratio

        try:
            sift_stack = sift_matcher_stack()
        except Exception:
            logger.exception("SIFT+LightGlue stack lookup failed")
            sift_stack = None
        if sift_stack is None:
            return glue_score, inliers, inlier_ratio

        _sift_name, sift_extractor, sift_matcher = sift_stack
        del _sift_name
        try:
            sift_glue, sift_inliers, sift_ratio = self._match_once(
                sift_extractor, sift_matcher, left_img, right_img
            )
        except Exception:
            logger.exception("SIFT+LightGlue fallback failed; keeping ALIKED inliers")
            return glue_score, inliers, inlier_ratio

        if sift_glue > 0.0 or sift_inliers > inliers:
            return sift_glue, sift_inliers, sift_ratio
        return glue_score, inliers, inlier_ratio

    def _match_with_rotations(
        self, extractor: object, matcher: object, left_img: Any, right_img: Any
    ) -> tuple[float, int, float]:
        import torch
        from torchvision.transforms.functional import to_tensor

        device = _module_device(matcher, feature_device())
        left_t = to_tensor(left_img).unsqueeze(0).to(device)
        with torch.inference_mode():
            left_dict = _features_to_lightglue(extractor(left_t), left_t)

        best: tuple[float, int, float] = (0.0, 0, 0.0)
        for angle in _ROTATION_ANGLES:
            if angle == 0:
                rotated = right_img
            else:
                rotated = right_img.rotate(angle, expand=True)
            glue_score, inliers, inlier_ratio = self._match_right(
                extractor, matcher, left_dict, rotated
            )
            if inliers > best[1] or (inliers == best[1] and glue_score > best[0]):
                best = (glue_score, inliers, inlier_ratio)
            if angle == 0 and inliers >= _ROTATION_EARLY_STOP:
                break
        return best

    def _match_once(
        self, extractor: object, matcher: object, left_img: Any, right_img: Any
    ) -> tuple[float, int, float]:
        import torch
        from torchvision.transforms.functional import to_tensor

        device = _module_device(matcher, feature_device())
        left_t = to_tensor(left_img).unsqueeze(0).to(device)
        with torch.inference_mode():
            left_dict = _features_to_lightglue(extractor(left_t), left_t)
        return self._match_right(extractor, matcher, left_dict, right_img)

    def _match_right(
        self,
        extractor: object,
        matcher: object,
        left_dict: dict,
        right_img: Any,
    ) -> tuple[float, int, float]:
        import torch
        from torchvision.transforms.functional import to_tensor

        device = _module_device(matcher, feature_device())
        right_t = to_tensor(right_img).unsqueeze(0).to(device)
        with torch.inference_mode():
            right_dict = _features_to_lightglue(extractor(right_t), right_t)
            left_on_device = _move_feature_dict(left_dict, device)
            matches = matcher({"image0": left_on_device, "image1": right_dict})
        return _score_lightglue_matches(left_on_device, right_dict, matches)


def _max_cosine(left_vecs: list[Any], right_vecs: list[Any]) -> float:
    import numpy as np

    best = -1.0
    for left in left_vecs:
        for right in right_vecs:
            cosine = float(np.dot(left, right))
            if cosine > best:
                best = cosine
    return best


def _module_device(module: object, fallback: str):
    import torch

    if hasattr(module, "parameters"):
        try:
            return next(module.parameters()).device  # type: ignore[operator]
        except StopIteration:
            pass
    return torch.device(fallback)


def _move_feature_dict(feature_dict: dict, device: Any) -> dict:
    moved: dict[str, Any] = {}
    for key, value in feature_dict.items():
        if hasattr(value, "to"):
            moved[key] = value.to(device)
        else:
            moved[key] = value
    return moved


def _features_to_lightglue(feature_batch: Any, image_tensor: Any) -> dict:
    """Adapt ALIKED/DISK/SIFT outputs into LightGlue's nested dict input."""
    import torch

    feat = feature_batch[0] if isinstance(feature_batch, (list, tuple)) else feature_batch
    extra: dict[str, Any] = {}
    if isinstance(feat, dict):
        keypoints = feat["keypoints"]
        descriptors = feat["descriptors"]
        for key in ("scales", "oris"):
            if key in feat:
                extra[key] = feat[key]
    else:
        keypoints = feat.keypoints
        descriptors = feat.descriptors
        for key in ("scales", "oris"):
            if hasattr(feat, key):
                extra[key] = getattr(feat, key)
    if keypoints.ndim == 2:
        keypoints = keypoints.unsqueeze(0)
    if descriptors.ndim == 2:
        descriptors = descriptors.unsqueeze(0)
    for key, value in list(extra.items()):
        if hasattr(value, "ndim") and value.ndim == 1:
            extra[key] = value.unsqueeze(0)
    # OpenCV SIFT returns CPU tensors; move them onto the matcher device.
    device = image_tensor.device
    keypoints = keypoints.to(device)
    descriptors = descriptors.to(device)
    for key, value in list(extra.items()):
        if hasattr(value, "to"):
            extra[key] = value.to(device)
    _, _, height, width = image_tensor.shape
    return {
        "keypoints": keypoints,
        "descriptors": descriptors,
        "image_size": torch.tensor(
            [[width, height]], device=device, dtype=torch.float32
        ),
        **extra,
    }


def _score_lightglue_matches(
    left_dict: dict, right_dict: dict, matches: Any
) -> tuple[float, int, float]:
    import numpy as np

    kpts0 = left_dict["keypoints"][0].detach().cpu().numpy()
    kpts1 = right_dict["keypoints"][0].detach().cpu().numpy()
    if kpts0.size == 0 or kpts1.size == 0:
        return 0.0, 0, 0.0

    matches0 = matches["matches0"]
    if isinstance(matches0, (list, tuple)):
        matches0 = matches0[0]
    matches0 = matches0.detach().cpu().numpy().reshape(-1)
    valid = matches0 >= 0
    pts0 = np.asarray(kpts0[valid], dtype=np.float32).reshape(-1, 2)
    pts1 = np.asarray(kpts1[matches0[valid].astype(int)], dtype=np.float32).reshape(-1, 2)
    total_matches = int(pts0.shape[0])
    if total_matches == 0:
        return 0.0, 0, 0.0

    inliers = count_geometric_inliers(pts0, pts1)
    inlier_ratio = float(inliers / total_matches) if total_matches else 0.0
    if inliers < _MIN_INLIERS:
        return 0.0, inliers, inlier_ratio
    glue_score = _clamp01(inliers / _INLIER_NORM) * inlier_ratio
    return float(glue_score), inliers, inlier_ratio
