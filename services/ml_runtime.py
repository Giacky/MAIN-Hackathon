"""Lazy local Hugging Face runtime for the Mac demo server."""

from __future__ import annotations

import os
from functools import lru_cache


CLASSIFIER_MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
TEXT_EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
IMAGE_EMBEDDING_MODEL_ID = "clip-ViT-B-32"


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
        # Photos are optional; text matching should still warm cleanly.
        pass
