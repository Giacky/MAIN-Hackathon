from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest

os.environ.setdefault("LOST_FOUND_MOCK_ML", "1")

from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from services.classifier import ReportClassifier
from services.geo_matching import GeoMatcher
from services.image_matching import ImageMatcher
from services.matching_engine import MatchingEngine
from services.time_matching import TimeMatcher


class SkeletonSmokeTests(unittest.TestCase):
    def test_service_contracts_are_callable(self) -> None:
        lost = Report(report_type=ReportType.LOST, description="black wallet")
        found = Report(report_type=ReportType.FOUND, description="dark wallet")

        classification = ReportClassifier().classify(lost.description)
        matches = MatchingEngine().rank_matches(lost, [found])

        self.assertIn("mock", classification.category)
        self.assertEqual(matches[0].found_report_id, found.id)
        self.assertEqual(matches[0].text_score, 0.5)
        self.assertIsNone(matches[0].image_score)

    def test_empty_description_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ReportClassifier().classify("   ")

    def test_sqlite_report_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            report = Report(report_type=ReportType.FOUND, description="silver key")
            repository.add_report(report)

            loaded = repository.get_report(report.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.description, "silver key")


class GeoTimeMatchingTests(unittest.TestCase):
    def test_geo_scores_inside_radius_as_one(self) -> None:
        lost = Report(
            report_type=ReportType.LOST,
            description="wallet",
            latitude=50.8514,
            longitude=5.6900,
            radius_meters=500,
        )
        found = Report(
            report_type=ReportType.FOUND,
            description="wallet",
            latitude=50.8514,
            longitude=5.6905,
            radius_meters=500,
        )
        result = GeoMatcher().compare(lost, found)
        self.assertIsNotNone(result.distance_meters)
        self.assertLess(result.distance_meters or 9999, 500)
        self.assertEqual(result.score, 1.0)

    def test_geo_missing_coords_is_zero(self) -> None:
        lost = Report(report_type=ReportType.LOST, description="wallet", latitude=50.85)
        found = Report(report_type=ReportType.FOUND, description="wallet")
        result = GeoMatcher().compare(lost, found)
        self.assertEqual(result.score, 0.0)
        self.assertIsNone(result.distance_meters)

    def test_time_same_moment_is_one(self) -> None:
        moment = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
        lost = Report(
            report_type=ReportType.LOST, description="keys", event_time=moment
        )
        found = Report(
            report_type=ReportType.FOUND, description="keys", event_time=moment
        )
        self.assertEqual(TimeMatcher().compare(lost, found), 1.0)

    def test_time_found_before_lost_is_downweighted(self) -> None:
        lost_time = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)
        earlier = lost_time - timedelta(hours=6)
        later = lost_time + timedelta(hours=6)
        lost = Report(
            report_type=ReportType.LOST, description="keys", event_time=lost_time
        )
        found_early = Report(
            report_type=ReportType.FOUND, description="keys", event_time=earlier
        )
        found_late = Report(
            report_type=ReportType.FOUND, description="keys", event_time=later
        )
        matcher = TimeMatcher()
        self.assertLess(matcher.compare(lost, found_early), matcher.compare(lost, found_late))


class ImageMatchingTests(unittest.TestCase):
    def test_missing_images_return_none(self) -> None:
        self.assertIsNone(ImageMatcher().compare((), ()))

    def test_mock_score_when_files_exist(self) -> None:
        with TemporaryDirectory() as directory:
            lost_path = Path(directory) / "lost.jpg"
            found_path = Path(directory) / "found.jpg"
            lost_path.write_bytes(b"fake")
            found_path.write_bytes(b"fake")
            score = ImageMatcher().compare([str(lost_path)], [str(found_path)])
        self.assertEqual(score, 0.5)


if __name__ == "__main__":
    unittest.main()
