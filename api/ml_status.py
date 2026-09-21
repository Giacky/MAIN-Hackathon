"""In-process ML warmup status for health endpoints."""

from __future__ import annotations

import logging
import threading
from typing import Literal

from services.ml_runtime import (
    dino_model,
    dino_processor,
    feature_matcher_stack,
    image_backend,
    inference_device,
    rembg_session,
    use_mock_ml,
    warmup_text_models,
)

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


def snapshot() -> dict:
    with _lock:
        models = dict(_models)
    if use_mock_ml():
        models = {key: "mock" for key in models}
    return {
        "status": "ok",
        "mock_ml": use_mock_ml(),
        "device": inference_device(),
        # "mock" or "dino_lightglue"; see services.ml_runtime.image_backend().
        "image_backend": image_backend(),
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

        # Same lru_cached loaders services.image_matching uses, so warmup primes
        # the exact objects the first real ranking request will hit. A failed
        # loader leaves that model "failed"; photo scores then come back as
        # None with an image_error and ranking continues on text/place/time.
        for key, loader in (
            ("dino", _try_load_dino),
            ("features", feature_matcher_stack),
            ("segmenter", rembg_session),
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
    dino_processor()
    dino_model()


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
