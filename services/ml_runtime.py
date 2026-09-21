"""Lazy local Hugging Face runtime for the Mac demo server."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)


CLASSIFIER_MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
TEXT_EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
IMAGE_EMBEDDING_MODEL_ID = "clip-ViT-B-32"
DINO_MODEL_ID = "facebook/dinov2-small"

_BACKEND_CLIP = "clip"
_BACKEND_DINO = "dino_lightglue"
_BACKEND_MOCK = "mock"


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
    """ALIKED / LightGlue stay on CPU — Kornia on MPS is a likely demo crash."""
    return "cpu"


def _forced_image_backend() -> str | None:
    raw = os.getenv("LOST_FOUND_IMAGE_BACKEND", "").strip().lower()
    if raw in {_BACKEND_CLIP, _BACKEND_DINO}:
        return raw
    return None


@lru_cache(maxsize=1)
def _kornia_feature_stack() -> tuple[str, object, object] | None:
    """Return (features_name, extractor, matcher) or None if unavailable."""
    device = feature_device()
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
        extractor = ALIKED(max_num_keypoints=512)
        matcher = LightGlue(features="aliked")
        extractor = extractor.to(device).eval()
        matcher = matcher.to(device).eval()
        return ("aliked", extractor, matcher)
    except Exception:
        logger.exception("ALIKED failed to load; trying DISK once")

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

        return ("disk", _DiskAdapter(extractor), matcher)
    except Exception:
        logger.exception("DISK feature stack also failed to load")
        return None


def vision_stack_available() -> bool:
    """True when DINOv2 shortlist + local-feature re-rank can be attempted."""
    if use_mock_ml():
        return False
    if _forced_image_backend() == _BACKEND_CLIP:
        return False
    return _kornia_feature_stack() is not None


def image_backend() -> str:
    """Active photo backend: mock, dino_lightglue, or clip."""
    if use_mock_ml():
        return _BACKEND_MOCK
    forced = _forced_image_backend()
    if forced == _BACKEND_CLIP:
        return _BACKEND_CLIP
    if forced == _BACKEND_DINO or forced is None:
        if vision_stack_available():
            return _BACKEND_DINO
        return _BACKEND_CLIP
    return _BACKEND_CLIP


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
def image_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(IMAGE_EMBEDDING_MODEL_ID, device=inference_device())


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


def warmup_text_models() -> None:
    """Load weights once on the Mac so the first phone request is not a cold start."""
    if use_mock_ml():
        return
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
    try:
        image_embedding_model()
    except Exception:
        logger.exception("CLIP image model failed to load during warmup")


def warmup_vision_models() -> None:
    """Load DINOv2, rembg, and ALIKED/LightGlue (or leave CLIP as fallback)."""
    if use_mock_ml():
        return
    if image_backend() == _BACKEND_CLIP:
        image_embedding_model()
        return
    dino_processor()
    dino_model()
    try:
        rembg_session()
    except Exception:
        logger.exception("rembg failed during vision warmup; full-frame crops will be used")
    feature_matcher_stack()
