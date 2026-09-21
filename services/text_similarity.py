"""Semantic text similarity boundary."""


class TextSimilarityService:
    """Compare two descriptions; a sentence transformer will replace this mock."""

    def compare(self, text_a: str, text_b: str) -> float:
        """Return a neutral placeholder score for two non-empty descriptions."""
        return 0.5 if text_a.strip() and text_b.strip() else 0.0
