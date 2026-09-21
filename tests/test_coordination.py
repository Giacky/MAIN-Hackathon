from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database.repository import SQLiteRepository
from models.schemas import Meetup, MeetupStatus, Report, ReportType, match_thread_id
from services.coordination import (
    DEMO_FINDER_USER_ID,
    DEMO_MIA_USER_ID,
    can_respond_to_meetup,
    contact_for_viewer,
    display_name_for_sender,
    ensure_demo_handoff_reports,
    role_for_user,
)


class CoordinationTests(unittest.TestCase):
    def test_finder_contact_stays_hidden_while_anonymous(self) -> None:
        finder = Report(
            report_type=ReportType.FOUND,
            description="wallet",
            contact_email="finder@example.com",
            contact_phone="06",
            prefer_anonymous=True,
        )

        email, phone = contact_for_viewer(finder, "lost")

        self.assertIsNone(email)
        self.assertIsNone(phone)
        self.assertEqual(contact_for_viewer(finder, "found"), ("finder@example.com", "06"))

    def test_owner_sees_finder_contact_after_they_opt_in(self) -> None:
        finder = Report(
            report_type=ReportType.FOUND,
            description="wallet",
            contact_email="finder@example.com",
            prefer_anonymous=False,
        )

        email, phone = contact_for_viewer(finder, "lost")

        self.assertEqual(email, "finder@example.com")
        self.assertIsNone(phone)

    def test_only_the_other_person_can_accept_a_meetup(self) -> None:
        meetup = Meetup(
            match_id="a:b",
            proposed_by="lost",
            location_name="Library",
            meeting_time=datetime.now() + timedelta(hours=2),
        )

        self.assertTrue(can_respond_to_meetup(meetup, "found"))
        self.assertFalse(can_respond_to_meetup(meetup, "lost"))

    def test_meetup_and_notes_round_trip(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            match_id = match_thread_id("lost-1", "found-1")
            meetup = Meetup(
                match_id=match_id,
                proposed_by="found",
                location_name="Hotel reception",
                meeting_time=datetime(2026, 9, 22, 15, 0),
            )
            repository.save_meetup(meetup)
            repository.update_meetup_status(match_id, MeetupStatus.ACCEPTED)

            loaded = repository.get_meetup(match_id)

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, MeetupStatus.ACCEPTED)
        self.assertEqual(loaded.location_name, "Hotel reception")

    def test_demo_seed_creates_anonymous_finder(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            ensure_demo_handoff_reports(repository)
            finder = repository.get_report("found-demo-456")
            hotel = repository.get_report("found-demo-789")

        self.assertTrue(finder.prefer_anonymous)
        self.assertEqual(finder.user_id, DEMO_FINDER_USER_ID)
        self.assertEqual(hotel.user_id, DEMO_MIA_USER_ID)
        self.assertFalse(hotel.prefer_anonymous)
        self.assertEqual(display_name_for_sender("found", "lost"), "Finder")

    def test_logged_in_owner_gets_lost_role(self) -> None:
        lost = Report(report_type=ReportType.LOST, description="x", user_id="u-owner")
        found = Report(report_type=ReportType.FOUND, description="y", user_id="u-finder")
        self.assertEqual(role_for_user("u-owner", lost, found), "lost")
        self.assertEqual(role_for_user("u-finder", lost, found), "found")
        self.assertIsNone(role_for_user("someone-else", lost, found))
        self.assertEqual(
            role_for_user(None, lost, found, email="owner@demo.local"),
            None,
        )
        lost.contact_email = "alex@demo.local"
        self.assertEqual(role_for_user(None, lost, found, email="alex@demo.local"), "lost")


if __name__ == "__main__":
    unittest.main()
