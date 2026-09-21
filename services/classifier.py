"""Report classification; DeBERTa zero-shot with a mock fallback."""

from models.schemas import ClassificationResult
from services.ml_runtime import use_mock_ml, zero_shot_pipeline

CATEGORY_LABELS = (
    "wallet",
    "keys",
    "phone",
    "laptop",
    "bag",
    "earbuds",
    "bottle",
    "glasses",
    "jewelry",
    "id or documents",
    "clothing",
    "other",
)
URGENCY_LABELS = ("high", "normal", "low")
SENSITIVE_LABELS = ("sensitive personal item", "not sensitive")

_CATEGORY_HYPOTHESIS = "This lost or found item is a {}."
_URGENCY_HYPOTHESIS = "The urgency of recovering this item is {}."
_SENSITIVE_HYPOTHESIS = "This item is a {}."


def _mock_result() -> ClassificationResult:
    return ClassificationResult(
        category="unclassified (mock)",
        urgency="normal (mock)",
        sensitive_item=False,
        recommended_handling="Store safely and await matching (mock).",
        category_confidence=None,
        urgency_confidence=None,
        sensitive_confidence=None,
        category_ranking=(),
        is_mock=True,
    )


def _zero_shot(
    sequence: str, labels: tuple[str, ...], hypothesis_template: str
) -> list[tuple[str, float]]:
    """Run one DeBERTa zero-shot pass; return labels sorted by score (best first)."""
    result = zero_shot_pipeline()(
        sequence,
        candidate_labels=list(labels),
        hypothesis_template=hypothesis_template,
        multi_label=False,
    )
    ranking = list(
        zip(
            [str(label) for label in result["labels"]],
            [float(score) for score in result["scores"]],
        )
    )
    return ranking


def _recommended_handling(category: str, urgency: str, sensitive_item: bool) -> str:
    if sensitive_item:
        return (
            "Do not photograph IDs, cards, or documents in detail. "
            "Store securely and hand to campus security."
        )
    if urgency == "high" or category in {"keys", "phone", "laptop", "id or documents"}:
        return "Keep the item in a safe place and prioritize matching."
    return "Store safely and await matching."


class ReportClassifier:
    """Classify free text without exposing a model to callers."""

    def classify(self, description: str) -> ClassificationResult:
        if not description.strip():
            raise ValueError("description must not be empty")
        if use_mock_ml():
            return _mock_result()

        try:
            category_ranking = _zero_shot(
                description, CATEGORY_LABELS, _CATEGORY_HYPOTHESIS
            )
            urgency_ranking = _zero_shot(
                description, URGENCY_LABELS, _URGENCY_HYPOTHESIS
            )
            sensitive_ranking = _zero_shot(
                description, SENSITIVE_LABELS, _SENSITIVE_HYPOTHESIS
            )
        except Exception:
            return _mock_result()

        category, category_confidence = category_ranking[0]
        urgency, urgency_confidence = urgency_ranking[0]
        sensitive_label, sensitive_confidence = sensitive_ranking[0]
        sensitive_item = sensitive_label == "sensitive personal item"

        return ClassificationResult(
            category=category,
            urgency=urgency,
            sensitive_item=sensitive_item,
            recommended_handling=_recommended_handling(
                category, urgency, sensitive_item
            ),
            category_confidence=category_confidence,
            urgency_confidence=urgency_confidence,
            sensitive_confidence=sensitive_confidence,
            category_ranking=tuple(category_ranking),
            is_mock=False,
        )
