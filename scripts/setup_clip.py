#!/usr/bin/env python3
"""Download and cache CLIP (clip-ViT-B-32) in the same env that runs Streamlit."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["LOST_FOUND_MOCK_ML"] = "0"

from PIL import Image

from services.ml_runtime import IMAGE_EMBEDDING_MODEL_ID, image_embedding_model, use_mock_ml
from utils.images import prepare_clip_image


def main() -> int:
    if use_mock_ml():
        print("LOST_FOUND_MOCK_ML is on. Unset it, then run this script again.", file=sys.stderr)
        return 1

    print(f"Loading SentenceTransformer({IMAGE_EMBEDDING_MODEL_ID!r})…")
    model = image_embedding_model()
    probe = prepare_clip_image(Image.new("RGB", (320, 240), (40, 90, 160)))
    vector = model.encode(probe, normalize_embeddings=True, convert_to_numpy=True)
    if vector is None or getattr(vector, "size", 0) == 0:
        print("CLIP returned an empty embedding.", file=sys.stderr)
        return 1

    dim = int(getattr(vector, "shape", [len(vector)])[-1])
    print(f"CLIP is ready. Embedding size: {dim}")
    print("Weights stay in the local Hugging Face cache (not in Git).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
