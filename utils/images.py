"""Normalize photos to the square size CLIP expects."""

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

CLIP_IMAGE_SIZE = 224


def prepare_clip_image(image: Image.Image, size: int = CLIP_IMAGE_SIZE) -> Image.Image:
    """Center-crop to a square, then resize for CLIP ViT-B/32."""
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    width, height = rgb.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    cropped = rgb.crop((left, top, left + side, top + side))
    return cropped.resize((size, size), Image.Resampling.LANCZOS)


def save_prepared_image(source: Path | bytes, destination: Path) -> Path:
    """Write a CLIP-sized JPEG next to the intended upload path."""
    destination = destination.with_suffix(".jpg")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(source, bytes):
        with Image.open(BytesIO(source)) as image:
            prepared = prepare_clip_image(image)
    else:
        with Image.open(source) as image:
            prepared = prepare_clip_image(image)
    prepared.save(destination, format="JPEG", quality=90)
    return destination
