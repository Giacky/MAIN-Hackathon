"""Geographic compatibility using Haversine distance and uncertainty radius."""

from dataclasses import dataclass
from math import atan2, cos, exp, radians, sin, sqrt

from models.schemas import Report

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
    """Haversine distance plus uncertainty-radius matching."""

    def compare(self, lost_report: Report, found_report: Report) -> GeoMatchResult:
        coordinates = (
            lost_report.latitude,
            lost_report.longitude,
            found_report.latitude,
            found_report.longitude,
        )
        lost_lat, lost_lon, found_lat, found_lon = coordinates
        if lost_lat is None or lost_lon is None or found_lat is None or found_lon is None:
            return GeoMatchResult(score=0.0, distance_meters=None)

        distance = haversine_meters(lost_lat, lost_lon, found_lat, found_lon)
        radius = lost_report.radius_meters or _DEFAULT_RADIUS_METERS
        if found_report.radius_meters:
            radius = min(radius, found_report.radius_meters)
        radius = max(radius, 1.0)

        if distance <= radius:
            score = 1.0
        else:
            score = exp(-(distance - radius) / radius)
        return GeoMatchResult(score=float(max(0.0, min(1.0, score))), distance_meters=distance)
