"""Lazy local Hugging Face runtime for the Mac demo server."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


CLASSIFIER_MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
TEXT_EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
DINO_MODEL_ID = "facebook/dinov2-small"

_BACKEND_DINO = "dino_lightglue"
_BACKEND_MOCK = "mock"

# Once ALIKED/LightGlue warmup fails on MPS, stay on CPU for this process.
_feature_device_override: str | None = None


def use_mock_ml() -> bool:
    """Keep CI and machines without weights on the original placeholder behavior."""
    flag = os.getenv("LOST_FOUND_MOCK_ML", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    return False


def inference_device() -> str:
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def feature_device() -> str:
    """ALIKED / LightGlue device. Prefer MPS; may fall back to CPU after warmup failure."""
    if _feature_device_override is not None:
        return _feature_device_override
    return inference_device()


def _set_feature_device(device: str) -> None:
    global _feature_device_override
    _feature_device_override = device


def _forced_image_backend() -> str | None:
    """LOST_FOUND_IMAGE_BACKEND only accepts dino_lightglue; anything else is ignored."""
    raw = os.getenv("LOST_FOUND_IMAGE_BACKEND", "").strip().lower()
    if not raw:
        return None
    if raw == _BACKEND_DINO:
        return raw
    logger.warning(
        "Unknown LOST_FOUND_IMAGE_BACKEND=%r; only %r is supported (set LOST_FOUND_MOCK_ML=1 for mock)",
        raw,
        _BACKEND_DINO,
    )
    return None


def _warmup_feature_forward(extractor: object, matcher: object, device: str) -> None:
    """One dummy ALIKED → LightGlue pass so MPS failures surface at startup."""
    import torch

    torch_device = torch.device(device)
    left = torch.rand(1, 3, 64, 64, device=torch_device)
    right = torch.rand(1, 3, 64, 64, device=torch_device)
    with torch.inference_mode():
        left_raw = extractor(left)
        right_raw = extractor(right)
        left_dict = _features_to_lightglue_dicts(left_raw, left)
        right_dict = _features_to_lightglue_dicts(right_raw, right)
        matcher({"image0": left_dict, "image1": right_dict})


def _features_to_lightglue_dicts(feature_batch: object, image_tensor: object) -> dict:
    """Minimal ALIKED/DISK → LightGlue dict (kept here to avoid import cycles)."""
    import torch

    feat = feature_batch[0] if isinstance(feature_batch, (list, tuple)) else feature_batch
    extra: dict[str, object] = {}
    if isinstance(feat, dict):
        keypoints = feat["keypoints"]
        descriptors = feat["descriptors"]
        for key in ("scales", "oris"):
            if key in feat:
                extra[key] = feat[key]
    else:
        keypoints = feat.keypoints  # type: ignore[attr-defined]
        descriptors = feat.descriptors  # type: ignore[attr-defined]
        for key in ("scales", "oris"):
            if hasattr(feat, key):
                extra[key] = getattr(feat, key)
    if getattr(keypoints, "ndim", 0) == 2:
        keypoints = keypoints.unsqueeze(0)  # type: ignore[union-attr]
    if getattr(descriptors, "ndim", 0) == 2:
        descriptors = descriptors.unsqueeze(0)  # type: ignore[union-attr]
    for key, value in list(extra.items()):
        if hasattr(value, "ndim") and value.ndim == 1:  # type: ignore[union-attr]
            extra[key] = value.unsqueeze(0)  # type: ignore[union-attr]
    _, _, height, width = image_tensor.shape  # type: ignore[union-attr]
    return {
        "keypoints": keypoints,
        "descriptors": descriptors,
        "image_size": torch.tensor(
            [[width, height]], device=image_tensor.device, dtype=torch.float32  # type: ignore[union-attr]
        ),
        **extra,
    }


def _build_aliked_stack(device: str) -> tuple[str, object, object] | None:
    try:
        from kornia.feature import ALIKED, LightGlue
    except ImportError:
        ALIKED = None  # type: ignore[assignment]
        LightGlue = None  # type: ignore[assignment]
        try:
            from lightglue import ALIKED, LightGlue  # type: ignore[no-redef]
        except ImportError:
            logger.info("Neither kornia.feature nor lightglue is importable")
            return None

    try:
        extractor = ALIKED(max_num_keypoints=1024)
        matcher = LightGlue(features="aliked")
        extractor = extractor.to(device).eval()
        matcher = matcher.to(device).eval()
        _warmup_feature_forward(extractor, matcher, device)
        return ("aliked", extractor, matcher)
    except Exception:
        logger.exception("ALIKED failed to load or warm up on %s; trying DISK once", device)

    try:
        from kornia.feature import DISK, LightGlue as LG
    except ImportError:
        try:
            from lightglue import DISK, LightGlue as LG  # type: ignore[no-redef]
        except ImportError:
            return None
    try:
        if hasattr(DISK, "from_pretrained"):
            extractor = DISK.from_pretrained("depth")
        else:
            extractor = DISK()
        matcher = LG(features="disk")
        extractor = extractor.to(device).eval()
        matcher = matcher.to(device).eval()

        # Wrap DISK so callers can pass a single image tensor like ALIKED.
        class _DiskAdapter:
            def __init__(self, model: object) -> None:
                self._model = model

            def __call__(self, images: object) -> object:
                return self._model(images, n=512)  # type: ignore[operator]

            def to(self, *args: object, **kwargs: object):
                self._model = self._model.to(*args, **kwargs)  # type: ignore[attr-defined]
                return self

            def eval(self):
                self._model = self._model.eval()  # type: ignore[attr-defined]
                return self

        adapter = _DiskAdapter(extractor)
        _warmup_feature_forward(adapter, matcher, device)
        return ("disk", adapter, matcher)
    except Exception:
        logger.exception("DISK feature stack also failed to load on %s", device)
        return None


@lru_cache(maxsize=1)
def _kornia_feature_stack() -> tuple[str, object, object] | None:
    """Return (features_name, extractor, matcher) or None if unavailable."""
    preferred = inference_device()
    stack = _build_aliked_stack(preferred)
    if stack is not None:
        _set_feature_device(preferred)
        logger.info("Feature stack (ALIKED/LightGlue) device=%s", preferred)
        return stack

    if preferred != "cpu":
        logger.warning(
            "ALIKED/LightGlue unavailable on %s; falling back to CPU for this process",
            preferred,
        )
        stack = _build_aliked_stack("cpu")
        if stack is not None:
            _set_feature_device("cpu")
            logger.info("Feature stack (ALIKED/LightGlue) device=cpu (fallback)")
            return stack

    _set_feature_device("cpu")
    logger.info("Feature stack (ALIKED/LightGlue) unavailable")
    return None


class _OpenCvSiftExtractor:
    """OpenCV SIFT in LightGlue dict form (keypoints, descriptors, scales, oris)."""

    def __init__(self, max_num_keypoints: int = 1024) -> None:
        import cv2

        self._max_num_keypoints = max_num_keypoints
        self._sift = cv2.SIFT_create(
            contrastThreshold=0.0066667,
            nfeatures=max_num_keypoints,
            edgeThreshold=10,
            nOctaveLayers=4,
        )

    def __call__(self, images: object) -> dict:
        import cv2
        import numpy as np
        import torch

        tensor = images if isinstance(images, torch.Tensor) else torch.as_tensor(images)
        if tensor.ndim == 3:
            tensor = tensor.unsqueeze(0)
        frame = tensor[0].detach().cpu()
        if frame.shape[0] == 3:
            rgb = (
                frame.permute(1, 2, 0).numpy().clip(0.0, 1.0) * 255.0
            ).astype(np.uint8)
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        else:
            gray = (frame[0].numpy().clip(0.0, 1.0) * 255.0).astype(np.uint8)

        detections, descriptors = self._sift.detectAndCompute(gray, None)
        if descriptors is None or not detections:
            empty = torch.zeros(1, 0, 2, dtype=torch.float32)
            return {
                "keypoints": empty,
                "descriptors": torch.zeros(1, 0, 128, dtype=torch.float32),
                "scales": torch.zeros(1, 0, dtype=torch.float32),
                "oris": torch.zeros(1, 0, dtype=torch.float32),
            }

        points = np.array([kp.pt for kp in detections], dtype=np.float32)
        scores = np.array([kp.response for kp in detections], dtype=np.float32)
        scales = np.array([kp.size for kp in detections], dtype=np.float32)
        angles = np.deg2rad(np.array([kp.angle for kp in detections], dtype=np.float32))
        if len(points) > self._max_num_keypoints:
            keep = np.argpartition(-scores, self._max_num_keypoints)[: self._max_num_keypoints]
            points, scores, scales, angles = (
                points[keep],
                scores[keep],
                scales[keep],
                angles[keep],
            )
            descriptors = descriptors[keep]

        desc = torch.from_numpy(np.asarray(descriptors, dtype=np.float32))
        desc = torch.nn.functional.normalize(desc, p=1, dim=-1, eps=1e-6)
        desc = desc.clamp_min(1e-6).sqrt()
        desc = torch.nn.functional.normalize(desc, p=2, dim=-1, eps=1e-6)
        return {
            "keypoints": torch.from_numpy(points).unsqueeze(0),
            "descriptors": desc.unsqueeze(0),
            "scales": torch.from_numpy(scales).unsqueeze(0),
            "oris": torch.from_numpy(angles).unsqueeze(0),
        }


@lru_cache(maxsize=1)
def _sift_feature_stack() -> tuple[str, object, object] | None:
    """SIFT extractor + LightGlue(features='sift'). Always CPU (OpenCV SIFT)."""
    device = "cpu"
    try:
        from kornia.feature import LightGlue
    except ImportError:
        try:
            from lightglue import LightGlue  # type: ignore[no-redef]
        except ImportError:
            logger.info("SIFT+LightGlue unavailable (LightGlue is not importable)")
            return None

    try:
        matcher = LightGlue(features="sift")
        matcher = matcher.to(device).eval()
        extractor = _OpenCvSiftExtractor(max_num_keypoints=1024)
        logger.info("SIFT stack device=cpu")
        return ("sift", extractor, matcher)
    except Exception:
        logger.exception(
            "SIFT+LightGlue failed to load; ALIKED misses will use DINOv2 cosine"
        )
        return None


def vision_stack_available() -> bool:
    """True when DINOv2 shortlist + local-feature re-rank can be attempted."""
    if use_mock_ml():
        return False
    return _kornia_feature_stack() is not None


def image_backend() -> str:
    """Active photo backend: mock or dino_lightglue.

    There is no secondary photo model. When the vision stack cannot load, photo
    scores come back as None with an image_error and ranking continues on
    description, place, and time.
    """
    if use_mock_ml():
        return _BACKEND_MOCK
    _forced_image_backend()  # only validates / warns about the env value
    return _BACKEND_DINO


@lru_cache(maxsize=1)
def zero_shot_pipeline():
    import torch
    from transformers import pipeline

    return pipeline(
        "zero-shot-classification",
        model=CLASSIFIER_MODEL_ID,
        device=torch.device(inference_device()),
    )


@lru_cache(maxsize=1)
def text_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(TEXT_EMBEDDING_MODEL_ID, device=inference_device())


@lru_cache(maxsize=1)
def dino_processor():
    from transformers import AutoImageProcessor

    return AutoImageProcessor.from_pretrained(DINO_MODEL_ID)


@lru_cache(maxsize=1)
def dino_model():
    import torch
    from transformers import AutoModel

    model = AutoModel.from_pretrained(DINO_MODEL_ID)
    model = model.to(torch.device(inference_device())).eval()
    return model


@lru_cache(maxsize=1)
def rembg_session():
    from rembg import new_session

    return new_session()


def feature_matcher_stack() -> tuple[str, object, object]:
    stack = _kornia_feature_stack()
    if stack is None:
        raise RuntimeError("Local feature matcher (ALIKED/LightGlue) is unavailable")
    return stack


def sift_matcher_stack() -> tuple[str, object, object] | None:
    """Optional SIFT+LightGlue fallback. None when weights or OpenCV SIFT cannot load."""
    return _sift_feature_stack()


def warmup_text_models() -> None:
    """Load weights once on the Mac so the first phone request is not a cold start."""
    if use_mock_ml():
        return
    device = inference_device()
    logger.info("Classifier device=%s", device)
    logger.info("Text embedding device=%s", device)
    pipeline = zero_shot_pipeline()
    pipeline(
        "black wallet",
        candidate_labels=["wallet", "keys"],
        hypothesis_template="This item is a {}.",
        multi_label=False,
    )
    text_embedding_model().encode(
        "warmup lost item description",
        normalize_embeddings=True,
        convert_to_numpy=True,
    )


def warmup_vision_models() -> None:
    """Load DINOv2, rembg, ALIKED/LightGlue, and SIFT+LightGlue if available."""
    if use_mock_ml():
        return
    logger.info("DINOv2 device=%s", inference_device())
    dino_processor()
    dino_model()
    try:
        rembg_session()
        logger.info("rembg device=cpu")
    except Exception:
        logger.exception("rembg failed during vision warmup; full-frame crops will be used")
    feature_matcher_stack()
    if _sift_feature_stack() is None:
        logger.info(
            "SIFT+LightGlue not loaded; ALIKED misses will use DINOv2 cosine"
        )
