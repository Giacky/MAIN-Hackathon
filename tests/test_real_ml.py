"""Live Hugging Face matching checks. Skipped unless RUN_REAL_ML=1."""

from __future__ import annotations

import os
import unittest

os.environ["LOST_FOUND_MOCK_ML"] = "0"

from models.schemas import Report, ReportType
from services.demo_seed import ensure_demo_data
from services.matching_engine import MatchingEngine
from services.ml_runtime import use_mock_ml
from services.text_similarity import TextSimilarityService


def _lost(description: str, **kwargs) -> Report:
    return Report(report_type=ReportType.LOST, description=description, **kwargs)


def _found(description: str, **kwargs) -> Report:
    return Report(report_type=ReportType.FOUND, description=description, **kwargs)


@unittest.skipUnless(os.getenv("RUN_REAL_ML", "").strip() == "1", "set RUN_REAL_ML=1")
class RealModelMatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ["LOST_FOUND_MOCK_ML"] = "0"
        if use_mock_ml():
            raise unittest.SkipTest("mock ML is still on")
        cls.text = TextSimilarityService()
        cls.engine = MatchingEngine()

    def test_models_are_not_mock(self) -> None:
        self.assertFalse(use_mock_ml())
        same = self.text.compare("black wallet", "black wallet")
        self.assertGreater(same, 0.9)

    def test_black_bag_vs_black_wallet_is_not_a_match(self) -> None:
        match = self.engine.rank_matches(
            _lost("black bag"),
            [_found("black wallet")],
        )[0]
        self.assertLess(match.text_score, 0.4)
        self.assertEqual(match.category_score, 0.0)
        self.assertEqual(match.overall_score, 0.0)

    def test_true_wallet_pair_survives(self) -> None:
        match = self.engine.rank_matches(
            _lost("Black leather wallet. Lost in the library."),
            [_found("Black leather wallet found at the library entrance.")],
        )[0]
        self.assertGreater(match.text_score, 0.5)
        self.assertGreater(match.overall_score, 0.35)

    def test_airpods_pair_survives(self) -> None:
        match = self.engine.rank_matches(
            _lost("White AirPods case. Lost at the bus stop."),
            [_found("White AirPods case found next to the bus stop.")],
        )[0]
        self.assertGreater(match.text_score, 0.7)
        self.assertGreater(match.overall_score, 0.5)

    def test_wallet_vs_airpods_is_rejected(self) -> None:
        match = self.engine.rank_matches(
            _lost("Black leather wallet. Lost in the library."),
            [_found("White AirPods case found next to the bus stop.")],
        )[0]
        self.assertEqual(match.overall_score, 0.0)

    def test_demo_seed_wallet_and_airpods(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        from database.repository import SQLiteRepository

        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "real-ml.sqlite")
            ensure_demo_data(repository)
            lost_reports = [
                report
                for report in repository.list_reports()
                if report.report_type == ReportType.LOST
            ]
            found_reports = [
                report
                for report in repository.list_reports()
                if report.report_type == ReportType.FOUND
            ]
            wallet_lost = next(r for r in lost_reports if "wallet" in r.description.lower())
            airpods_lost = next(r for r in lost_reports if "airpods" in r.description.lower())

            wallet_matches = {
                m.found_report_id: m
                for m in self.engine.rank_matches(wallet_lost, found_reports)
            }
            airpods_matches = {
                m.found_report_id: m
                for m in self.engine.rank_matches(airpods_lost, found_reports)
            }

        wallet_found = next(r for r in found_reports if "library" in r.description.lower())
        airpods_found = next(r for r in found_reports if "airpods" in r.description.lower())
        hotel_found = next(r for r in found_reports if "hotel" in r.description.lower())

        self.assertGreater(wallet_matches[wallet_found.id].overall_score, 0.5)
        self.assertEqual(wallet_matches[airpods_found.id].overall_score, 0.0)
        self.assertEqual(wallet_matches[hotel_found.id].overall_score, 0.0)
        self.assertGreater(airpods_matches[airpods_found.id].overall_score, 0.7)
        self.assertEqual(airpods_matches[wallet_found.id].overall_score, 0.0)

    def test_rotated_crop_of_same_photo_still_scores(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from PIL import Image

        from services.image_matching import ImageMatcher

        src = Path("samples/images/lost_black_wallet.png")
        if not src.is_file():
            self.skipTest("sample wallet photo missing")
        matcher = ImageMatcher()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "orig.png"
            rotated = root / "rot90.png"
            with Image.open(src) as image:
                rgb = image.convert("RGB")
                rgb.save(original)
                rgb.rotate(90, expand=True).save(rotated)
            result = matcher.compare([str(original)], [str(rotated)])
        self.assertIsNotNone(result.score)
        self.assertGreater(result.score, 0.0)
        self.assertTrue(result.shortlisted)


if __name__ == "__main__":
    unittest.main()
