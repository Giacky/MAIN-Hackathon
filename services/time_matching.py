"""Temporal compatibility boundary."""

from models.schemas import Report


class TimeMatcher:
    """Placeholder for elapsed-time scoring."""

    def compare(self, lost_report: Report, found_report: Report) -> float:
        """Return a neutral score when both reports include an event time."""
        if lost_report.event_time is None or found_report.event_time is None:
            return 0.0
        return 0.5
