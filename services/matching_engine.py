"""Coordinator for independently replaceable matching signals."""

from collections.abc import Iterable

from models.schemas import MatchResult, Report, ReportType
from services.geo_matching import GeoMatcher
from services.image_matching import ImageMatcher
from services.item_type import resolved_item_type
from services.text_similarity import TextSimilarityService
from services.time_matching import TimeMatcher

# Text still leads, but photos and place carry more of the decision.
_WEIGHT_TEXT = 0.42
_WEIGHT_IMAGE = 0.33
_WEIGHT_GEO = 0.16
_WEIGHT_TIME = 0.09

# Hard gates: cross-type / weak text cannot be rescued by location/time.
TEXT_SCORE_FLOOR = 0.50


def _type_value(report: Report) -> str:
    """Compare report types by value so Streamlit hot-reload enum identity cannot break matching."""
    report_type = report.report_type
    if isinstance(report_type, ReportType):
        return report_type.value
    return str(report_type).lower()


def category_compatibility(lost_report: Report, found_report: Report) -> float | None:
    """1.0 same type, 0.0 different, None if either side has no usable type.

    Uses the saved category when present, otherwise keywords in the description
    so "black bag" vs "black wallet" is rejected even if embeddings are close.
    """
    left = resolved_item_type(lost_report)
    right = resolved_item_type(found_report)
    if left is None or right is None:
        return None
    return 1.0 if left == right else 0.0


def weighted_overall(
    text_score: float,
    geo_score: float,
    time_score: float,
    image_score: float | None,
    category_score: float | None = None,
) -> float:
    """Weighted blend before gates. Category is a hard gate, not part of the blend.

    Missing photos (`image_score is None`) are left out and the remaining weights
    are renormalized, so no picture is never treated as a 0% photo score.
    """
    del category_score  # kept in signature for call-site compatibility
    parts: list[tuple[float, float]] = [
        (text_score, _WEIGHT_TEXT),
        (geo_score, _WEIGHT_GEO),
        (time_score, _WEIGHT_TIME),
    ]
    if image_score is not None:
        parts.append((image_score, _WEIGHT_IMAGE))
    total_weight = sum(weight for _, weight in parts)
    if total_weight <= 0:
        return 0.0
    score = sum(value * weight for value, weight in parts) / total_weight
    return float(max(0.0, min(1.0, score)))


def apply_match_gates(
    text_score: float,
    category_score: float | None,
    blended_score: float,
) -> float:
    """Zero out pairs that fail category or text floors."""
    if category_score == 0.0:
        return 0.0
    if text_score < TEXT_SCORE_FLOOR:
        return 0.0
    return blended_score


def gate_reason(text_score: float, category_score: float | None) -> str | None:
    if category_score == 0.0:
        return "category mismatch (hard gate)"
    if text_score < TEXT_SCORE_FLOOR:
        return f"text score below floor ({TEXT_SCORE_FLOOR:.0%})"
    return None


class MatchingEngine:
    """Combine matching services behind one UI-facing interface."""

    def __init__(
        self,
        text_matcher: TextSimilarityService | None = None,
        geo_matcher: GeoMatcher | None = None,
        time_matcher: TimeMatcher | None = None,
        image_matcher: ImageMatcher | None = None,
    ) -> None:
        self.text_matcher = text_matcher or TextSimilarityService()
        self.geo_matcher = geo_matcher or GeoMatcher()
        self.time_matcher = time_matcher or TimeMatcher()
        self.image_matcher = image_matcher or ImageMatcher()

    def rank_matches(
        self, lost_report: Report, found_reports: Iterable[Report]
    ) -> list[MatchResult]:
        """Rank found reports; category mismatch / weak text are hard-gated to 0."""
        if _type_value(lost_report) != ReportType.LOST.value:
            raise ValueError(
                f"lost_report must have report_type=LOST (got {_type_value(lost_report)!r})"
            )

        results: list[MatchResult] = []
        for found_report in found_reports:
            if _type_value(found_report) != ReportType.FOUND.value:
                continue
            text_score = self.text_matcher.compare(
                lost_report.description, found_report.description
            )
            geo = self.geo_matcher.compare(lost_report, found_report)
            time_score = self.time_matcher.compare(lost_report, found_report)
            image = self.image_matcher.compare(
                lost_report.image_paths, found_report.image_paths
            )
            category_score = category_compatibility(lost_report, found_report)
            blended = weighted_overall(
                text_score,
                geo.score,
                time_score,
                image.score,
                category_score,
            )
            overall = apply_match_gates(text_score, category_score, blended)
            results.append(
                MatchResult(
                    lost_report_id=lost_report.id,
                    found_report_id=found_report.id,
                    overall_score=overall,
                    text_score=text_score,
                    image_score=image.score,
                    category_score=category_score,
                    geo_score=geo.score,
                    time_score=time_score,
                    distance_meters=geo.distance_meters,
                    image_error=image.error,
                )
            )
        return sorted(results, key=lambda match: match.overall_score, reverse=True)
