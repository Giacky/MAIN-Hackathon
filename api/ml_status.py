"""In-process ML warmup status for health endpoints."""

from __future__ import annotations

import logging
import os
import threading
from typing import Literal

from services.ml_runtime import inference_device, use_mock_ml, warmup_text_models

logger = logging.getLogger(__name__)

ModelState = Literal["idle", "warming", "ready", "mock", "failed"]

_lock = threading.Lock()
_models: dict[str, ModelState] = {
    "classifier": "idle",
    "text": "idle",
    "dino": "idle",
    "features": "idle",
    "segmenter": "idle",
}
_warmup_thread: threading.Thread | None = None


def _image_backend() -> str:
    if use_mock_ml():
        return "mock"
    forced = os.getenv("LOST_FOUND_IMAGE_BACKEND", "").strip().lower()
    if forced == "clip":
        return "clip"
    return "dino_lightglue"


def snapshot() -> dict:
    with _lock:
        models = dict(_models)
    if use_mock_ml():
        models = {key: "mock" for key in models}
    return {
        "status": "ok",
        "mock_ml": use_mock_ml(),
        "device": inference_device(),
        "image_backend": _image_backend(),
        "models": models,
    }


def _set_many(updates: dict[str, ModelState]) -> None:
    with _lock:
        _models.update(updates)


def _run_warmup() -> None:
    try:
        if use_mock_ml():
            _set_many({key: "mock" for key in _models})
            return

        _set_many({"classifier": "warming", "text": "warming"})
        try:
            warmup_text_models()
            _set_many({"classifier": "ready", "text": "ready"})
        except Exception:
            logger.exception("Text model warmup failed")
            _set_many({"classifier": "failed", "text": "failed"})

        for key, loader in (
            ("dino", _try_load_dino),
            ("features", _try_load_features),
            ("segmenter", _try_load_segmenter),
        ):
            _set_many({key: "warming"})
            try:
                loader()
                _set_many({key: "ready"})
            except Exception:
                logger.exception("Warmup failed for %s", key)
                _set_many({key: "failed"})
    finally:
        global _warmup_thread
        with _lock:
            _warmup_thread = None


def _try_load_dino() -> None:
    from transformers import AutoModel

    # Use cache only so API warmup does not start a multi-minute download.
    AutoModel.from_pretrained("facebook/dinov2-small", local_files_only=True)


def _try_load_features() -> None:
    try:
        from kornia.feature import ALIKED, LightGlue  # noqa: F401
    except Exception:
        import lightglue  # noqa: F401


def _try_load_segmenter() -> None:
    import rembg  # noqa: F401


def start_warmup() -> str:
    """Start background warmup; return warming / mock state for the response."""
    if use_mock_ml():
        _set_many({key: "mock" for key in _models})
        return "mock"

    global _warmup_thread
    with _lock:
        if _warmup_thread is not None and _warmup_thread.is_alive():
            return "warming"
        _warmup_thread = threading.Thread(target=_run_warmup, daemon=True)
        _warmup_thread.start()
    return "warming"
