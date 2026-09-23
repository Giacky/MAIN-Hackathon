"""Coordinator for independently replaceable matching signals."""

from collections.abc import Iterable

from models.schemas import MatchResult, Report, ReportType
from services.geo_matching import GeoMatcher
from services.image_matching import ImageCompareResult, ImageMatcher
from services.item_type import resolved_item_type
from services.text_similarity import TextSimilarityService, apply_type_match_text_floor
from services.time_matching import TimeMatcher

# Text still leads, but photos and place carry more of the decision.
_WEIGHT_TEXT = 0.42
_WEIGHT_IMAGE = 0.33
_WEIGHT_GEO = 0.16
_WEIGHT_TIME = 0.09

# Hard gate: cross-type cannot be rescued by location/time.
# (No text-score floor — weak text can still rank via photos / place.)


def _type_value(report: Report) -> str:
    """Compare report types by value so enum identity across module reloads cannot break matching."""
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
    """Zero out pairs that fail the category gate."""
    del text_score  # kept for call-site compatibility
    if category_score == 0.0:
        return 0.0
    return blended_score


def gate_reason(text_score: float, category_score: float | None) -> str | None:
    del text_score  # kept for call-site compatibility
    if category_score == 0.0:
        return "category mismatch (hard gate)"
    return None


def _visual_fields(image: ImageCompareResult) -> dict:
    """Copy shortlist evidence onto MatchResult only when a photo score exists."""
    if image.score is None or not image.shortlisted:
        return {
            "visual_shortlisted": None,
            "visual_dino_score": None,
            "visual_inliers": None,
            "visual_inlier_ratio": None,
            "visual_same_object": None,
        }
    return {
        "visual_shortlisted": True,
        "visual_dino_score": image.dino_score,
        "visual_inliers": image.inliers,
        "visual_inlier_ratio": image.inlier_ratio,
        "visual_same_object": image.same_object,
    }


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
        """Rank found reports; category mismatch is hard-gated to 0."""
        if _type_value(lost_report) != ReportType.LOST.value:
            raise ValueError(
                f"lost_report must have report_type=LOST (got {_type_value(lost_report)!r})"
            )

        found_list = [
            found_report
            for found_report in found_reports
            if _type_value(found_report) == ReportType.FOUND.value
        ]
        image_by_id = self.image_matcher.score_candidates(
            lost_report.image_paths,
            tuple((found.id, found.image_paths) for found in found_list),
        )

        results: list[MatchResult] = []
        for found_report in found_list:
            text_score = self.text_matcher.compare(
                lost_report.description, found_report.description
            )
            text_score = apply_type_match_text_floor(
                text_score,
                resolved_item_type(lost_report),
                resolved_item_type(found_report),
                lost_report.description,
                found_report.description,
            )
            geo = self.geo_matcher.compare(lost_report, found_report)
            time_score = self.time_matcher.compare(lost_report, found_report)
            image = image_by_id.get(
                found_report.id, ImageCompareResult(score=None)
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
                    **_visual_fields(image),
                )
            )
        return sorted(results, key=lambda match: match.overall_score, reverse=True)
