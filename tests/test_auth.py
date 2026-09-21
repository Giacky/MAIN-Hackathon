from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from database.repository import SQLiteRepository
from models.schemas import Report, ReportType, User
from services.auth import hash_password, verify_password
from services.coordination import DEMO_ACCOUNTS, DEMO_PASSWORD, ensure_demo_handoff_reports


class AuthTests(unittest.TestCase):
    def test_password_round_trip(self) -> None:
        stored = hash_password("secret-demo")
        self.assertTrue(verify_password("secret-demo", stored))
        self.assertFalse(verify_password("wrong", stored))

    def test_create_user_and_lookup_by_email(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            repository.add_user(
                User(
                    email="luuk@demo.local",
                    display_name="Luuk",
                    password_hash=hash_password("pass"),
                )
            )
            loaded = repository.get_user_by_email("LUUK@demo.local")

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.display_name, "Luuk")
        self.assertTrue(verify_password("pass", loaded.password_hash))

    def test_report_is_listed_for_its_owner(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            user = repository.add_user(
                User(
                    email="owner@demo.local",
                    display_name="Owner",
                    password_hash=hash_password("pass"),
                )
            )
            repository.add_report(
                Report(
                    report_type=ReportType.LOST,
                    description="black wallet",
                    user_id=user.id,
                )
            )
            mine = repository.list_reports_for_user(user.id)

        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0].user_id, user.id)

    def test_demo_login_accounts_exist(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            ensure_demo_handoff_reports(repository)
            loaded = [
                repository.get_user_by_email(account.email) for account in DEMO_ACCOUNTS
            ]

        self.assertEqual(len(loaded), len(DEMO_ACCOUNTS))
        for account, user in zip(DEMO_ACCOUNTS, loaded, strict=True):
            self.assertIsNotNone(user)
            self.assertEqual(user.display_name, account.display_name)
            self.assertTrue(verify_password(DEMO_PASSWORD, user.password_hash))

    def test_every_demo_persona_has_lost_and_found_items(self) -> None:
        with TemporaryDirectory() as directory:
            repository = SQLiteRepository(Path(directory) / "test.sqlite")
            ensure_demo_handoff_reports(repository)
            per_user = {
                account.user_id: repository.list_reports_for_user(account.user_id)
                for account in DEMO_ACCOUNTS
            }

        for account in DEMO_ACCOUNTS:
            kinds = {report.report_type for report in per_user[account.user_id]}
            self.assertEqual(kinds, {ReportType.LOST, ReportType.FOUND}, account.email)
            self.assertRegex(account.avatar, r"^#[0-9A-Fa-f]{6}$")
            self.assertTrue(account.summary.startswith("Lost "), account.summary)
            self.assertIn("found", account.summary)
        self.assertEqual(len({account.avatar for account in DEMO_ACCOUNTS}), len(DEMO_ACCOUNTS))


if __name__ == "__main__":
    unittest.main()
