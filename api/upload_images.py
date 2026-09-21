"""Local upload helper until vision lands utils.images.save_upload_image."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

# Vision owns utils.images.save_upload_image; call that when present.
_MAX_SIDE = 1280


def save_upload_image(source: Path | bytes, destination: Path) -> Path:
    """Write an EXIF-transposed aspect-ratio JPEG (longest side <= 1280)."""
    # Vision owns utils.images.save_upload_image; prefer it when available.
    from utils import images as images_mod

    shared = getattr(images_mod, "save_upload_image", None)
    if shared is not None and shared is not save_upload_image:
        return shared(source, destination)

    destination = destination.with_suffix(".jpg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(source, bytes):
        image = Image.open(BytesIO(source))
    else:
        image = Image.open(source)
    with image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
        width, height = rgb.size
        longest = max(width, height)
        if longest > _MAX_SIDE:
            scale = _MAX_SIDE / float(longest)
            rgb = rgb.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )
        rgb.save(destination, format="JPEG", quality=90)
    return destination
