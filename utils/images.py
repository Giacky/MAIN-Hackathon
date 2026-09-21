"""Normalize uploaded photos for display storage."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

UPLOAD_MAX_SIDE = 1280


def prepare_upload_image(
    image: Image.Image, max_side: int = UPLOAD_MAX_SIDE
) -> Image.Image:
    """EXIF-transpose and shrink so the longest side fits max_side (keep aspect ratio)."""
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    width, height = rgb.size
    longest = max(width, height)
    if longest <= max_side:
        return rgb
    scale = max_side / float(longest)
    new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    return rgb.resize(new_size, Image.Resampling.LANCZOS)


def save_upload_image(source: Path | bytes, destination: Path) -> Path:
    """Write a display JPEG (max side 1280, aspect ratio preserved)."""
    destination = destination.with_suffix(".jpg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(source, bytes):
        with Image.open(BytesIO(source)) as image:
            prepared = prepare_upload_image(image)
    else:
        with Image.open(source) as image:
            prepared = prepare_upload_image(image)
    prepared.save(destination, format="JPEG", quality=90)
    return destination
