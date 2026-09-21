"""Coordinator for independently replaceable matching signals."""

from collections.abc import Iterable

from models.schemas import MatchResult, Report, ReportType
from services.geo_matching import GeoMatcher
from services.image_matching import ImageMatcher
from services.text_similarity import TextSimilarityService
from services.time_matching import TimeMatcher


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
        """Produce placeholder rankings while keeping the eventual contract stable."""
        if lost_report.report_type is not ReportType.LOST:
            raise ValueError("lost_report must have report_type=LOST")

        results: list[MatchResult] = []
        for found_report in found_reports:
            if found_report.report_type is not ReportType.FOUND:
                continue
            text_score = self.text_matcher.compare(
                lost_report.description, found_report.description
            )
            geo = self.geo_matcher.compare(lost_report, found_report)
            time_score = self.time_matcher.compare(lost_report, found_report)
            image_score = self.image_matcher.compare(
                lost_report.image_paths, found_report.image_paths
            )
            active_scores = [text_score, geo.score, time_score]
            if image_score is not None:
                active_scores.append(image_score)
            results.append(
                MatchResult(
                    lost_report_id=lost_report.id,
                    found_report_id=found_report.id,
                    overall_score=sum(active_scores) / len(active_scores),
                    text_score=text_score,
                    image_score=image_score,
                    geo_score=geo.score,
                    time_score=time_score,
                    distance_meters=geo.distance_meters,
                )
            )
        return sorted(results, key=lambda match: match.overall_score, reverse=True)
