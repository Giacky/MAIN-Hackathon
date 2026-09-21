"""Geographic compatibility boundary."""

from dataclasses import dataclass

from models.schemas import Report


@dataclass(frozen=True, slots=True)
class GeoMatchResult:
    score: float
    distance_meters: float | None


class GeoMatcher:
    """Placeholder for Haversine distance plus uncertainty-radius matching."""

    def compare(self, lost_report: Report, found_report: Report) -> GeoMatchResult:
        """Return a neutral score when both reports include coordinates."""
        coordinates = (
            lost_report.latitude,
            lost_report.longitude,
            found_report.latitude,
            found_report.longitude,
        )
        if any(value is None for value in coordinates):
            return GeoMatchResult(score=0.0, distance_meters=None)
        return GeoMatchResult(score=0.5, distance_meters=None)
