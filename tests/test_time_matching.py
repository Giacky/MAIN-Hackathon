from datetime import datetime, timezone
import unittest

from models.schemas import Report, ReportType, as_utc
from services.time_matching import TimeMatcher


class TimeMatchingTests(unittest.TestCase):
    def test_aware_vs_aware_same_moment_is_one(self) -> None:
        moment = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
        lost = Report(
            report_type=ReportType.LOST, description="keys", event_time=moment
        )
        found = Report(
            report_type=ReportType.FOUND, description="keys", event_time=moment
        )
        self.assertEqual(TimeMatcher().compare(lost, found), 1.0)

    def test_naive_legacy_vs_aware_does_not_raise(self) -> None:
        aware = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
        naive = datetime(2026, 9, 21, 12, 0)
        lost = Report(
            report_type=ReportType.LOST, description="keys", event_time=naive
        )
        found = Report(
            report_type=ReportType.FOUND, description="keys", event_time=aware
        )
        self.assertEqual(TimeMatcher().compare(lost, found), 1.0)

    def test_missing_event_times_score_zero(self) -> None:
        lost = Report(report_type=ReportType.LOST, description="keys")
        found = Report(
            report_type=ReportType.FOUND,
            description="keys",
            event_time=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(TimeMatcher().compare(lost, found), 0.0)
        self.assertEqual(
            TimeMatcher().compare(
                Report(
                    report_type=ReportType.LOST,
                    description="keys",
                    event_time=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
                ),
                Report(report_type=ReportType.FOUND, description="keys"),
            ),
            0.0,
        )

    def test_as_utc_treats_naive_as_utc(self) -> None:
        naive = datetime(2026, 9, 21, 12, 0)
        aware = as_utc(naive)
        self.assertIsNotNone(aware)
        assert aware is not None
        self.assertEqual(aware.tzinfo, timezone.utc)
        self.assertEqual(aware.replace(tzinfo=None), naive)


class DatabaseDatetimeRoundTripTests(unittest.TestCase):
    def test_row_to_report_parses_naive_event_time_as_utc(self) -> None:
        from database.models import _parse_datetime

        parsed = _parse_datetime("2026-09-21T12:00:00")
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.hour, 12)

    def test_row_to_report_keeps_aware_event_time_in_utc(self) -> None:
        from database.models import _parse_datetime

        parsed = _parse_datetime("2026-09-21T14:00:00+02:00")
        self.assertEqual(parsed, datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc))
