from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from services.classifier import ReportClassifier
from services.matching_engine import MatchingEngine


class SkeletonSmokeTests(unittest.TestCase):
    def test_service_contracts_are_callable(self) -> None:
        lost = Report(report_type=ReportType.LOST, description="black wallet")
        found = Report(report_type=ReportType.FOUND, description="dark wallet")

        classification = ReportClassifier().classify(lost.description)
        matches = MatchingEngine().rank_matches(lost, [found])

        self.assertIn("mock", classification.category)
        self.assertEqual(matches[0].found_report_id, found.id)

    def test_sqlite_report_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            report = Report(report_type=ReportType.FOUND, description="silver key")
            repository.add_report(report)

            loaded = repository.get_report(report.id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.description, "silver key")


if __name__ == "__main__":
    unittest.main()
