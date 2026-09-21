"""Optional image similarity boundary; no vision model is loaded."""

from collections.abc import Sequence


class ImageMatcher:
    """Placeholder for DINOv2, SigLIP, or CLIP image embeddings."""

    def compare(
        self, lost_images: Sequence[str], found_images: Sequence[str]
    ) -> float | None:
        """Return None to clearly signal that image matching is unavailable."""
        return None
