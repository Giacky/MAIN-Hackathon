"""Geographic compatibility using Haversine distance and uncertainty radius."""

from dataclasses import dataclass
from math import atan2, cos, exp, radians, sin, sqrt

from models.schemas import Report
from utils.locations import report_points

_EARTH_RADIUS_METERS = 6_371_000.0
_DEFAULT_RADIUS_METERS = 500.0


@dataclass(frozen=True, slots=True)
class GeoMatchResult:
    score: float
    distance_meters: float | None


def haversine_meters(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    lat1, lon1, lat2, lon2 = map(
        radians, (latitude_a, longitude_a, latitude_b, longitude_b)
    )
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    chord = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_METERS * atan2(sqrt(chord), sqrt(1 - chord))


class GeoMatcher:
    """Haversine distance plus uncertainty-radius matching across all location pins."""

    def compare(self, lost_report: Report, found_report: Report) -> GeoMatchResult:
        lost_points = report_points(lost_report)
        found_points = report_points(found_report)
        if not lost_points or not found_points:
            return GeoMatchResult(score=0.0, distance_meters=None)

        best_score = -1.0
        best_distance: float | None = None
        for lost_lat, lost_lon, lost_radius in lost_points:
            for found_lat, found_lon, found_radius in found_points:
                distance = haversine_meters(lost_lat, lost_lon, found_lat, found_lon)
                radius = min(
                    lost_radius or _DEFAULT_RADIUS_METERS,
                    found_radius or _DEFAULT_RADIUS_METERS,
                )
                radius = max(radius, 1.0)
                score = 1.0 if distance <= radius else exp(-(distance - radius) / radius)
                score = float(max(0.0, min(1.0, score)))
                if score > best_score or (
                    score == best_score
                    and best_distance is not None
                    and distance < best_distance
                ):
                    best_score = score
                    best_distance = distance

        return GeoMatchResult(score=max(0.0, best_score), distance_meters=best_distance)
