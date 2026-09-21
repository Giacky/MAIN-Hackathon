#!/usr/bin/env python3
"""Download and cache DINOv2, rembg, ALIKED, and LightGlue for photo matching."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["LOST_FOUND_MOCK_ML"] = "0"
# Prefer the vision stack for this setup script.
os.environ.pop("LOST_FOUND_IMAGE_BACKEND", None)

from PIL import Image

from services.ml_runtime import (
    DINO_MODEL_ID,
    dino_model,
    dino_processor,
    feature_matcher_stack,
    image_backend,
    rembg_session,
    use_mock_ml,
)


def main() -> int:
    if use_mock_ml():
        print("LOST_FOUND_MOCK_ML is on. Unset it, then run this script again.", file=sys.stderr)
        return 1

    probe = Image.new("RGB", (320, 240), (40, 90, 160))

    print(f"Loading DINOv2 ({DINO_MODEL_ID})…")
    try:
        processor = dino_processor()
        model = dino_model()
        import torch

        inputs = processor(images=probe, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            outputs = model(**inputs)
            cls = outputs.last_hidden_state[:, 0]
            dim = int(cls.shape[-1])
        print(f"DINOv2 ready. CLS size: {dim}")
    except Exception as exc:
        print(f"FAILED at DINOv2: {exc}", file=sys.stderr)
        return 1

    print("Loading rembg session…")
    try:
        rembg_session()
        print("rembg ready.")
    except Exception as exc:
        print(f"FAILED at rembg (crops will use full frame): {exc}", file=sys.stderr)
        # Not fatal for matching — continue to feature stack.

    print("Loading ALIKED / LightGlue (CPU)…")
    try:
        features_name, _extractor, _matcher = feature_matcher_stack()
        print(f"Feature matcher ready ({features_name}).")
    except Exception as exc:
        print(f"FAILED at feature matcher: {exc}", file=sys.stderr)
        print(
            "CLIP remains available as automatic fallback "
            f"(image_backend={image_backend()!r}).",
            file=sys.stderr,
        )
        return 1

    print(f"Vision stack ready. image_backend={image_backend()!r}")
    print("Weights stay in the local Hugging Face / rembg caches (not in Git).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
