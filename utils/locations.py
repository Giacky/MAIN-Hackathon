"""Turn a report into map / matching coordinates."""

from models.schemas import Report

_DEFAULT_RADIUS_METERS = 500.0


def report_points(report: Report) -> list[tuple[float, float, float]]:
    """Return (latitude, longitude, radius_meters) from pins, else the primary point."""
    if report.locations:
        return [
            (item.latitude, item.longitude, item.radius_meters)
            for item in report.locations
        ]
    if report.latitude is None or report.longitude is None:
        return []
    return [
        (
            report.latitude,
            report.longitude,
            report.radius_meters or _DEFAULT_RADIUS_METERS,
        )
    ]
