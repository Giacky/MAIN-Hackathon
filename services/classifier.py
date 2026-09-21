"""Report classification boundary; replace the mock with DeBERTa later."""

from models.schemas import ClassificationResult


class ReportClassifier:
    """Classify free text without exposing a model to callers."""

    def classify(self, description: str) -> ClassificationResult:
        """Return an explicit mock result until the zero-shot model is wired in."""
        if not description.strip():
            raise ValueError("description must not be empty")
        return ClassificationResult(
            category="unclassified (mock)",
            urgency="normal (mock)",
            sensitive_item=False,
            recommended_handling="Store safely and await matching (mock).",
        )
