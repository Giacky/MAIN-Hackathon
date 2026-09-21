#!/usr/bin/env python3
"""Strip the flat dark letterbox / pillarbox bars from the sample photos in place.

Every file in samples/images was exported as 640x480 with bars padding the real
photo. The bars are a uniform dark grey (about 36/255), not pure black, so a
row or column is treated as "bar" when it is both dark (mean below a threshold)
and flat (tiny standard deviation). Dark but textured photo edges are kept.

    python scripts/crop_samples.py            # crop samples/images/*.png in place
    python scripts/crop_samples.py --dry-run  # only report the boxes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = ROOT / "samples" / "images"

# A bar row/column must be darker than this (0-255 grayscale mean)...
DARK_THRESHOLD = 48.0
# ...and flat: real photo content has far more variation than this.
FLAT_THRESHOLD = 4.0
# Never crop to something smaller than this fraction of the original side.
MIN_KEEP_FRACTION = 0.4


def _trim_bounds(means: np.ndarray, stds: np.ndarray) -> tuple[int, int]:
    """Return (start, end) indexes after dropping bar rows/columns from both ends."""
    is_bar = (means < DARK_THRESHOLD) & (stds < FLAT_THRESHOLD)
    start = 0
    end = len(means)
    while start < end and is_bar[start]:
        start += 1
    while end > start and is_bar[end - 1]:
        end -= 1
    return start, end


def detect_crop_box(image: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box (left, top, right, bottom) of the photo without its bars."""
    gray = np.asarray(ImageOps.exif_transpose(image).convert("L"), dtype=np.float32)
    height, width = gray.shape
    top, bottom = _trim_bounds(gray.mean(axis=1), gray.std(axis=1))
    left, right = _trim_bounds(gray.mean(axis=0), gray.std(axis=0))

    if (right - left) < width * MIN_KEEP_FRACTION or (bottom - top) < height * MIN_KEEP_FRACTION:
        # Almost everything looks like a bar; refuse to crop rather than destroy the image.
        return (0, 0, width, height)
    return (left, top, right, bottom)


def crop_file(path: Path, *, dry_run: bool = False) -> tuple[tuple[int, int], tuple[int, int]]:
    with Image.open(path) as image:
        rgb = ImageOps.exif_transpose(image).convert("RGB")
    box = detect_crop_box(rgb)
    before = rgb.size
    cropped = rgb.crop(box)
    after = cropped.size
    if not dry_run and after != before:
        cropped.save(path, format="PNG", optimize=True)
    return before, after


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report only, do not write")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="PNG files to crop (default: every PNG in samples/images)",
    )
    args = parser.parse_args(argv)

    targets = args.paths or sorted(SAMPLES_DIR.glob("*.png"))
    if not targets:
        print(f"No PNG files found in {SAMPLES_DIR}", file=sys.stderr)
        return 1

    for path in targets:
        before, after = crop_file(path, dry_run=args.dry_run)
        if before == after:
            status = "unchanged"
        else:
            status = "would crop" if args.dry_run else "cropped"
        print(f"{path.name}: {before[0]}x{before[1]} -> {after[0]}x{after[1]} ({status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
