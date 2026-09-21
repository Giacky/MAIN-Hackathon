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
from services.matching_engine import (
    MatchingEngine,
    apply_match_gates,
    weighted_overall,
)
from services.text_similarity import calibrate_text_cosine
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
        self.assertIsNone(matches[0].image_error)

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

    def test_geo_uses_closest_location_pin(self) -> None:
        from models.schemas import LocationGuess

        lost = Report(
            report_type=ReportType.LOST,
            description="wallet",
            locations=(
                LocationGuess(latitude=50.8514, longitude=5.6900, radius_meters=200),
                LocationGuess(latitude=52.3702, longitude=4.8952, radius_meters=200),
            ),
        )
        found = Report(
            report_type=ReportType.FOUND,
            description="wallet",
            latitude=50.8514,
            longitude=5.6901,
            radius_meters=200,
        )
        result = GeoMatcher().compare(lost, found)
        self.assertEqual(result.score, 1.0)
        self.assertIsNotNone(result.distance_meters)
        self.assertLess(result.distance_meters or 9999, 200)

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
        result = ImageMatcher().compare((), ())
        self.assertIsNone(result.score)
        self.assertIsNone(result.error)

    def test_mock_score_when_files_exist(self) -> None:
        with TemporaryDirectory() as directory:
            lost_path = Path(directory) / "lost.jpg"
            found_path = Path(directory) / "found.jpg"
            lost_path.write_bytes(b"fake")
            found_path.write_bytes(b"fake")
            result = ImageMatcher().compare([str(lost_path)], [str(found_path)])
        self.assertEqual(result.score, 0.5)
        self.assertIsNone(result.error)

    def test_clip_failure_is_not_treated_as_missing_photo(self) -> None:
        matcher = ImageMatcher()
        with TemporaryDirectory() as directory:
            lost_path = Path(directory) / "lost.jpg"
            found_path = Path(directory) / "found.jpg"
            lost_path.write_bytes(b"fake")
            found_path.write_bytes(b"fake")
            matcher._embed = lambda path: (_ for _ in ()).throw(RuntimeError("clip down"))
            os.environ["LOST_FOUND_MOCK_ML"] = "0"
            try:
                result = matcher.compare([str(lost_path)], [str(found_path)])
            finally:
                os.environ["LOST_FOUND_MOCK_ML"] = "1"
        self.assertIsNone(result.score)
        self.assertIsNotNone(result.error)
        self.assertIn("CLIP", result.error)


class ImagePrepTests(unittest.TestCase):
    def test_center_crop_resizes_to_clip_square(self) -> None:
        from PIL import Image

        from utils.images import CLIP_IMAGE_SIZE, prepare_clip_image, save_prepared_image

        wide = Image.new("RGB", (640, 240), color=(20, 80, 160))
        prepared = prepare_clip_image(wide)
        self.assertEqual(prepared.size, (CLIP_IMAGE_SIZE, CLIP_IMAGE_SIZE))

        with TemporaryDirectory() as directory:
            source = Path(directory) / "wide.png"
            wide.save(source)
            saved = save_prepared_image(source, Path(directory) / "out.png")
            with Image.open(saved) as loaded:
                self.assertEqual(loaded.size, (CLIP_IMAGE_SIZE, CLIP_IMAGE_SIZE))
                self.assertEqual(saved.suffix, ".jpg")


class WeightingTests(unittest.TestCase):
    def test_text_dominates_equal_geo_time(self) -> None:
        high_text = weighted_overall(0.9, 1.0, 1.0, None, None)
        low_text = weighted_overall(0.2, 1.0, 1.0, None, None)
        self.assertGreater(high_text, low_text)
        self.assertGreater(high_text - low_text, 0.2)

    def test_category_mismatch_is_hard_gated(self) -> None:
        blended = weighted_overall(0.9, 1.0, 1.0, 0.9, None)
        self.assertEqual(apply_match_gates(0.9, 0.0, blended), 0.0)

    def test_weak_text_is_not_hard_gated(self) -> None:
        blended = weighted_overall(0.2, 1.0, 1.0, 0.9, None)
        self.assertEqual(apply_match_gates(0.2, 1.0, blended), blended)

    def test_same_category_strong_text_passes(self) -> None:
        blended = weighted_overall(0.8, 1.0, 0.9, 0.7, None)
        self.assertEqual(apply_match_gates(0.8, 1.0, blended), blended)

    def test_black_bag_vs_black_wallet_is_rejected(self) -> None:
        lost = Report(report_type=ReportType.LOST, description="black bag")
        found = Report(report_type=ReportType.FOUND, description="black wallet")
        match = MatchingEngine().rank_matches(lost, [found])[0]
        self.assertEqual(match.category_score, 0.0)
        self.assertEqual(match.overall_score, 0.0)

    def test_missing_image_is_not_scored_as_zero(self) -> None:
        no_photo = weighted_overall(0.9, 0.5, 0.5, None)
        zero_photo = weighted_overall(0.9, 0.5, 0.5, 0.0)
        with_photo = weighted_overall(0.9, 0.5, 0.5, 0.9)
        self.assertGreater(no_photo, zero_photo)
        self.assertAlmostEqual(no_photo, (0.9 * 0.42 + 0.5 * 0.16 + 0.5 * 0.09) / 0.67)
        self.assertGreater(no_photo, 0.7)
        self.assertGreater(with_photo, zero_photo)


class GateRankingTests(unittest.TestCase):
    def test_cross_category_ranks_at_zero(self) -> None:
        lost = Report(
            report_type=ReportType.LOST,
            description="black wallet",
            category="wallet",
        )
        founds = [
            Report(
                report_type=ReportType.FOUND,
                description="black wallet near library",
                category="wallet",
            ),
            Report(
                report_type=ReportType.FOUND,
                description="silver keys with blue fob",
                category="keys",
            ),
        ]
        matches = MatchingEngine().rank_matches(lost, founds)
        by_id = {match.found_report_id: match for match in matches}
        self.assertGreater(by_id[founds[0].id].overall_score, 0.0)
        self.assertEqual(by_id[founds[1].id].overall_score, 0.0)
        self.assertEqual(by_id[founds[1].id].category_score, 0.0)


class TextCalibrationTests(unittest.TestCase):
    def test_typical_unrelated_cosine_collapses(self) -> None:
        self.assertEqual(calibrate_text_cosine(0.70), 0.0)
        self.assertEqual(calibrate_text_cosine(0.63), 0.0)

    def test_near_duplicate_stays_high(self) -> None:
        self.assertGreater(calibrate_text_cosine(0.95), 0.8)
        self.assertEqual(calibrate_text_cosine(1.0), 1.0)

    def test_black_wallet_vs_black_bag_raw_is_not_a_match(self) -> None:
        self.assertLess(calibrate_text_cosine(0.789), 0.35)


if __name__ == "__main__":
    unittest.main()
