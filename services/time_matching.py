"""Temporal compatibility from elapsed time between report events."""

from math import exp

from models.schemas import Report, as_utc

_DECAY_HOURS = 48.0
_FOUND_BEFORE_LOST_FACTOR = 0.5


class TimeMatcher:
    """Score how compatible two event times are."""

    def compare(self, lost_report: Report, found_report: Report) -> float:
        lost_time = as_utc(lost_report.event_time)
        found_time = as_utc(found_report.event_time)
        if lost_time is None or found_time is None:
            return 0.0

        hours_apart = abs((found_time - lost_time).total_seconds()) / 3600.0
        score = exp(-hours_apart / _DECAY_HOURS)
        if found_time < lost_time:
            score *= _FOUND_BEFORE_LOST_FACTOR
        return float(max(0.0, min(1.0, score)))
