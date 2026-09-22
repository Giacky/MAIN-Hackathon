"""FastAPI contract tests with mock ML and a temporary SQLite database."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ["LOST_FOUND_MOCK_ML"] = "1"
os.environ.pop("LOST_FOUND_ALLOW_DEMO_RESET", None)

from fastapi.testclient import TestClient
from PIL import Image

from api.deps import set_repository_override
from api.main import create_app
from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from services.demo_seed import (
    AVATAR_PALETTE,
    DEMO_ACCOUNTS,
    DEMO_FOUND_EARBUDS_ID,
    DEMO_FOUND_HOTEL_ID,
    DEMO_FOUND_LIBRARY_ID,
    DEMO_LOST_EARBUDS_ID,
    DEMO_LOST_ID,
    DEMO_PASSWORD,
    ensure_demo_data,
)
from services.match_jobs import enqueue
from utils.config import UPLOAD_DIR


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["LOST_FOUND_MOCK_ML"] = "1"
        os.environ.pop("LOST_FOUND_ALLOW_DEMO_RESET", None)
        self._tmpdir = TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        db_path = Path(self._tmpdir.name) / "test.sqlite"
        self.repository = SQLiteRepository(db_path)
        ensure_demo_data(self.repository, prune_extras=False)
        set_repository_override(self.repository)
        self.addCleanup(lambda: set_repository_override(None))
        self.app = create_app()
        # Enter the client context so lifespan seeds + enqueues missing pairs.
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def _login(self, email: str, password: str = DEMO_PASSWORD) -> dict:
        response = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_register_and_login_cookie(self) -> None:
        register = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Luuk",
                "email": "luuk@example.com",
                "password": "pass",
            },
        )
        self.assertEqual(register.status_code, 200, register.text)
        self.assertEqual(register.json()["user"]["email"], "luuk@example.com")
        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["display_name"], "Luuk")

        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

        login = self.client.post(
            "/api/auth/login",
            json={"email": "luuk@example.com", "password": "pass"},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)

    def test_wrong_password_is_401(self) -> None:
        response = self.client.post(
            "/api/auth/login",
            json={"email": "alex@demo.local", "password": "nope"},
        )
        self.assertEqual(response.status_code, 401)

    def test_demo_accounts_are_public_and_login_returns_avatar(self) -> None:
        response = self.client.get("/api/auth/demo-accounts")
        self.assertEqual(response.status_code, 200, response.text)
        accounts = response.json()["accounts"]
        self.assertEqual(len(accounts), len(DEMO_ACCOUNTS))
        for account, expected in zip(accounts, DEMO_ACCOUNTS, strict=True):
            self.assertEqual(set(account), {"name", "email", "avatar", "summary"})
            self.assertEqual(account["name"], expected.display_name)
            self.assertEqual(account["email"], expected.email)
            self.assertIn(account["avatar"], AVATAR_PALETTE)
            self.assertTrue(account["summary"].startswith("Lost "))
        emails = {account["email"] for account in accounts}
        self.assertEqual(
            emails,
            {"alex@demo.local", "sam@demo.local", "mia@demo.local", "noor@demo.local"},
        )
        alex = next(item for item in accounts if item["email"] == "alex@demo.local")
        self.assertEqual(alex["summary"], "Lost a wallet and AirPods, found keys and a backpack")

        login = self._login("noor@demo.local")
        noor = next(item for item in accounts if item["email"] == "noor@demo.local")
        self.assertEqual(login["user"]["avatar"], noor["avatar"])
        self.assertEqual(login["user"]["display_name"], "Noor Bakker")
        me = self.client.get("/api/auth/me").json()["user"]
        self.assertEqual(me["avatar"], noor["avatar"])

        # Non-demo users still get a palette color, and it is stable per id.
        register = self.client.post(
            "/api/auth/register",
            json={"display_name": "Luuk", "email": "luuk@example.com", "password": "pass"},
        )
        self.assertEqual(register.status_code, 200, register.text)
        avatar = register.json()["user"]["avatar"]
        self.assertIn(avatar, AVATAR_PALETTE)
        self.assertEqual(self.client.get("/api/auth/me").json()["user"]["avatar"], avatar)

    def test_create_multipart_report_and_safe_image_url(self) -> None:
        self._login("alex@demo.local")
        image = Image.new("RGB", (1600, 900), color=(20, 40, 60))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        locations = json.dumps(
            [{"latitude": 50.85, "longitude": 5.69, "radius_meters": 200}]
        )
        started = datetime.now(timezone.utc)
        response = self.client.post(
            "/api/reports",
            data={
                "report_type": "lost",
                "description": "Blue phone in a cracked case",
                "event_time": datetime.now(timezone.utc).isoformat(),
                "prefer_anonymous": "false",
                "locations": locations,
            },
            files={"images": ("phone.jpg", buffer, "image/jpeg")},
        )
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertLess(
            elapsed,
            2.0,
            f"create_report took {elapsed:.2f}s under mock ML (should stay fast)",
        )
        payload = response.json()
        report = payload["report"]
        self.assertIn("classification", payload)
        self.assertTrue(report["image_urls"])
        self.assertNotIn("image_paths", report)
        blob = json.dumps(report)
        self.assertNotIn("data/uploads", blob)
        self.assertFalse(any(url.startswith("/") is False for url in report["image_urls"]))
        for url in report["image_urls"]:
            self.assertTrue(url.startswith("/api/reports/"))
            self.assertNotIn(str(UPLOAD_DIR), url)

        image_response = self.client.get(report["image_urls"][0])
        self.assertEqual(image_response.status_code, 200)
        self.assertTrue(image_response.content.startswith(b"\xff\xd8"))
        with Image.open(BytesIO(image_response.content)) as saved:
            self.assertLessEqual(max(saved.size), 1280)
            self.assertNotEqual(saved.size[0], saved.size[1])

    def test_open_list_omits_contact(self) -> None:
        response = self.client.get("/api/reports?scope=open")
        self.assertEqual(response.status_code, 200)
        for report in response.json()["reports"]:
            self.assertNotIn("contact_email", report)
            self.assertNotIn("contact_phone", report)

    def test_seeded_matches_are_ready_and_ordered(self) -> None:
        self._login("alex@demo.local")
        response = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["anchor"]["id"], DEMO_LOST_ID)
        matches = payload["matches"]
        self.assertTrue(matches)
        found_ids = [match["found"]["id"] for match in matches]
        self.assertIn(DEMO_FOUND_LIBRARY_ID, found_ids)
        self.assertIn(DEMO_FOUND_HOTEL_ID, found_ids)
        self.assertLess(
            found_ids.index(DEMO_FOUND_LIBRARY_ID),
            found_ids.index(DEMO_FOUND_HOTEL_ID),
            "Sam's library wallet should rank above Mia's brown card holder",
        )

    def test_second_matches_get_does_not_rank(self) -> None:
        self._login("alex@demo.local")
        first = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["status"], "ready")

        from unittest.mock import patch

        with patch(
            "services.matching_engine.MatchingEngine.rank_matches",
            side_effect=AssertionError("rank_matches must not run on GET"),
        ) as rank:
            second = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(second.json()["status"], "ready")
        self.assertEqual(second.json()["matches"], first.json()["matches"])
        rank.assert_not_called()

    def test_rank_returns_component_scores_and_gate_reason(self) -> None:
        self._login("alex@demo.local")
        # Add a phone found report owned by someone else for category gate.
        other = self.repository.get_user_by_email("mia@demo.local")
        assert other is not None
        self.repository.add_report(
            Report(
                id="found-phone-gate",
                report_type=ReportType.FOUND,
                description="Blue smartphone in a cracked case on a cafe table.",
                category="phone",
                user_id=other.id,
                contact_email=other.email,
            )
        )
        enqueue("found-phone-gate")
        response = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "ready")
        matches = body["matches"]
        self.assertTrue(matches)
        top = matches[0]
        for key in (
            "overall_score",
            "text_score",
            "image_score",
            "category_score",
            "geo_score",
            "time_score",
            "gate_reason",
            "visual",
            "lost",
            "found",
        ):
            self.assertIn(key, top)
        for match in matches:
            if match["image_score"] is None:
                self.assertIsNone(match["visual"])
            else:
                self.assertEqual(
                    set(match["visual"]),
                    {"shortlisted", "dino_score", "inliers", "inlier_ratio"},
                )
                self.assertIsInstance(match["visual"]["shortlisted"], bool)
        phone_match = next(
            (
                match
                for match in matches
                if "phone" in match["found"]["description"].lower()
            ),
            None,
        )
        self.assertIsNotNone(phone_match)
        self.assertEqual(phone_match["gate_reason"], "category mismatch (hard gate)")
        self.assertEqual(phone_match["overall_score"], 0)

    def test_anonymous_finder_contact_hidden_from_owner(self) -> None:
        self._login("alex@demo.local")
        response = self.client.get(
            f"/api/coordination/{DEMO_LOST_ID}/{DEMO_FOUND_LIBRARY_ID}"
        )
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["role"], "lost")
        self.assertIsNone(payload["other_contact"])

    def test_proposer_cannot_accept_own_meetup_other_can(self) -> None:
        self._login("alex@demo.local")
        propose = self.client.post(
            f"/api/coordination/{DEMO_LOST_ID}/{DEMO_FOUND_LIBRARY_ID}/meetup",
            json={
                "location_name": "University library entrance",
                "meeting_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.assertEqual(propose.status_code, 200, propose.text)

        forbidden = self.client.post(
            f"/api/coordination/{DEMO_LOST_ID}/{DEMO_FOUND_LIBRARY_ID}/meetup/accept"
        )
        self.assertEqual(forbidden.status_code, 403)

        self.client.post("/api/auth/logout")
        self._login("sam@demo.local")
        accepted = self.client.post(
            f"/api/coordination/{DEMO_LOST_ID}/{DEMO_FOUND_LIBRARY_ID}/meetup/accept"
        )
        self.assertEqual(accepted.status_code, 200, accepted.text)
        self.assertEqual(accepted.json()["meetup"]["status"], "accepted")

    def test_coordination_list_requires_auth(self) -> None:
        self.assertEqual(self.client.get("/api/coordination").status_code, 401)

    def test_coordination_list_shows_active_threads_sorted(self) -> None:
        self._login("alex@demo.local")
        # No meetups or messages yet: nothing to list.
        empty = self.client.get("/api/coordination")
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json(), {"threads": []})

        # Alex proposes a meetup on the wallet thread.
        propose = self.client.post(
            f"/api/coordination/{DEMO_LOST_ID}/{DEMO_FOUND_LIBRARY_ID}/meetup",
            json={
                "location_name": "University library entrance",
                "meeting_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.assertEqual(propose.status_code, 200, propose.text)
        # Then sends a message on the AirPods thread (more recent activity).
        message = self.client.post(
            f"/api/coordination/{DEMO_LOST_EARBUDS_ID}/{DEMO_FOUND_EARBUDS_ID}/messages",
            json={"message": "Still have them?"},
        )
        self.assertEqual(message.status_code, 200, message.text)

        response = self.client.get("/api/coordination")
        self.assertEqual(response.status_code, 200, response.text)
        threads = response.json()["threads"]
        self.assertEqual(len(threads), 2)
        for thread in threads:
            self.assertEqual(
                set(thread),
                {"lost", "found", "role", "meetup_status", "last_message", "recovered"},
            )
            self.assertEqual(thread["role"], "lost")
            self.assertFalse(thread["recovered"])
            self.assertIn("contact_email", thread["lost"])
            self.assertNotIn("image_paths", thread["lost"])

        # Most recent activity first.
        self.assertEqual(threads[0]["lost"]["id"], DEMO_LOST_EARBUDS_ID)
        self.assertEqual(threads[0]["found"]["id"], DEMO_FOUND_EARBUDS_ID)
        self.assertEqual(threads[0]["meetup_status"], "none")
        self.assertEqual(threads[0]["last_message"], "Still have them?")
        self.assertEqual(threads[1]["lost"]["id"], DEMO_LOST_ID)
        self.assertEqual(threads[1]["found"]["id"], DEMO_FOUND_LIBRARY_ID)
        self.assertEqual(threads[1]["meetup_status"], "proposed")
        self.assertIsNone(threads[1]["last_message"])

        # Recovered threads sort last even when their activity is newest.
        recovered = self.client.post(
            f"/api/coordination/{DEMO_LOST_EARBUDS_ID}/{DEMO_FOUND_EARBUDS_ID}/recovered"
        )
        self.assertEqual(recovered.status_code, 200, recovered.text)
        threads = self.client.get("/api/coordination").json()["threads"]
        self.assertEqual(threads[0]["lost"]["id"], DEMO_LOST_ID)
        self.assertEqual(threads[1]["lost"]["id"], DEMO_LOST_EARBUDS_ID)
        self.assertTrue(threads[1]["recovered"])

        # The finder sees the same wallet thread from the found side, anonymous contact hidden.
        self.client.post("/api/auth/logout")
        self._login("sam@demo.local")
        sam_threads = self.client.get("/api/coordination").json()["threads"]
        self.assertEqual(len(sam_threads), 1)
        self.assertEqual(sam_threads[0]["role"], "found")
        self.assertEqual(sam_threads[0]["found"]["id"], DEMO_FOUND_LIBRARY_ID)
        self.assertIn("contact_email", sam_threads[0]["found"])
        self.assertNotIn("contact_email", sam_threads[0]["lost"])

        # Noor is not a party to any thread.
        self.client.post("/api/auth/logout")
        self._login("noor@demo.local")
        self.assertEqual(self.client.get("/api/coordination").json(), {"threads": []})

    def test_recovered_flips_both_statuses(self) -> None:
        self._login("alex@demo.local")
        response = self.client.post(
            f"/api/coordination/{DEMO_LOST_ID}/{DEMO_FOUND_LIBRARY_ID}/recovered"
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["recovered"])
        lost = self.repository.get_report(DEMO_LOST_ID)
        found = self.repository.get_report(DEMO_FOUND_LIBRARY_ID)
        assert lost is not None and found is not None
        self.assertEqual(lost.status.value, "recovered")
        self.assertEqual(found.status.value, "recovered")

    def test_demo_reset_forbidden_when_flag_off(self) -> None:
        os.environ.pop("LOST_FOUND_ALLOW_DEMO_RESET", None)
        response = self.client.post(
            "/api/demo/reset",
            headers={"X-Demo-Reset": "demo"},
        )
        self.assertEqual(response.status_code, 403)

    def test_close_report_drops_from_open_and_ranking(self) -> None:
        self._login("sam@demo.local")
        forbidden = self.client.patch(
            f"/api/reports/{DEMO_LOST_ID}/status",
            json={"status": "closed"},
        )
        self.assertEqual(forbidden.status_code, 403)

        self.client.post("/api/auth/logout")
        self._login("alex@demo.local")
        closed = self.client.patch(
            f"/api/reports/{DEMO_LOST_ID}/status",
            json={"status": "closed"},
        )
        self.assertEqual(closed.status_code, 200, closed.text)
        self.assertEqual(closed.json()["report"]["status"], "closed")
        stored = self.repository.get_report(DEMO_LOST_ID)
        assert stored is not None
        self.assertEqual(stored.status.value, "closed")

        invalid = self.client.patch(
            f"/api/reports/{DEMO_LOST_EARBUDS_ID}/status",
            json={"status": "open"},
        )
        self.assertEqual(invalid.status_code, 400)

        open_ids = {
            report["id"]
            for report in self.client.get("/api/reports?scope=open").json()["reports"]
        }
        self.assertNotIn(DEMO_LOST_ID, open_ids)

        self.client.post("/api/auth/logout")
        self._login("sam@demo.local")
        sam_matches = self.client.get(
            f"/api/matches?report_id={DEMO_FOUND_LIBRARY_ID}"
        )
        self.assertEqual(sam_matches.status_code, 200, sam_matches.text)
        lost_ids = [match["lost"]["id"] for match in sam_matches.json()["matches"]]
        self.assertNotIn(DEMO_LOST_ID, lost_ids)

        other = self.repository.get_user_by_email("mia@demo.local")
        assert other is not None
        new_found_id = "found-after-close"
        self.repository.add_report(
            Report(
                id=new_found_id,
                report_type=ReportType.FOUND,
                description="Black leather wallet at the desk.",
                category="wallet",
                user_id=other.id,
                contact_email=other.email,
            )
        )
        enqueue(new_found_id)
        pairs = {
            (match.lost_report_id, match.found_report_id)
            for match in self.repository.list_matches()
        }
        self.assertNotIn((DEMO_LOST_ID, new_found_id), pairs)

    def test_dismiss_match_omits_pair_and_survives_rerank(self) -> None:
        self._login("alex@demo.local")
        before = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(before.status_code, 200, before.text)
        self.assertIn(
            DEMO_FOUND_LIBRARY_ID,
            [match["found"]["id"] for match in before.json()["matches"]],
        )

        self.client.post("/api/auth/logout")
        self._login("sam@demo.local")
        dismissed = self.client.patch(
            "/api/matches/dismiss",
            json={
                "lost_report_id": DEMO_LOST_ID,
                "found_report_id": DEMO_FOUND_LIBRARY_ID,
            },
        )
        self.assertEqual(dismissed.status_code, 200, dismissed.text)
        self.assertTrue(dismissed.json()["dismissed"])

        self.client.post("/api/auth/logout")
        self._login("alex@demo.local")
        after = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(after.status_code, 200, after.text)
        self.assertNotIn(
            DEMO_FOUND_LIBRARY_ID,
            [match["found"]["id"] for match in after.json()["matches"]],
        )

        enqueue(DEMO_LOST_ID)
        reranked = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(reranked.status_code, 200, reranked.text)
        self.assertNotIn(
            DEMO_FOUND_LIBRARY_ID,
            [match["found"]["id"] for match in reranked.json()["matches"]],
        )

    def test_match_notification_for_counterpart_then_mark_read(self) -> None:
        self.assertEqual(self.client.get("/api/notifications").status_code, 401)

        register = self.client.post(
            "/api/auth/register",
            json={
                "display_name": "Luuk",
                "email": "luuk-notify@example.com",
                "password": "pass",
            },
        )
        self.assertEqual(register.status_code, 200, register.text)
        locations = json.dumps(
            [{"latitude": 50.8514, "longitude": 5.6900, "radius_meters": 200}]
        )
        created = self.client.post(
            "/api/reports",
            data={
                "report_type": "found",
                "description": "Black leather wallet found at the cafe.",
                "event_time": datetime.now(timezone.utc).isoformat(),
                "prefer_anonymous": "false",
                "locations": locations,
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        found_id = created.json()["report"]["id"]

        filer = self.client.get("/api/notifications")
        self.assertEqual(filer.status_code, 200, filer.text)
        self.assertFalse(
            any(
                item["found_report_id"] == found_id
                for item in filer.json()["notifications"]
            )
        )

        self.client.post("/api/auth/logout")
        self._login("alex@demo.local")
        payload = self.client.get("/api/notifications")
        self.assertEqual(payload.status_code, 200, payload.text)
        body = payload.json()
        self.assertIn("unread_count", body)
        note = next(
            (
                item
                for item in body["notifications"]
                if item["found_report_id"] == found_id
                and item["lost_report_id"] == DEMO_LOST_ID
            ),
            None,
        )
        self.assertIsNotNone(note)
        self.assertEqual(note["kind"], "match")
        self.assertIsNone(note["read_at"])
        self.assertGreater(note["overall_score"], 0)
        self.assertGreaterEqual(body["unread_count"], 1)
        self.assertIsNone(body["notifications"][0]["read_at"])

        marked = self.client.post(f"/api/notifications/{note['id']}/read")
        self.assertEqual(marked.status_code, 200, marked.text)
        self.assertIsNotNone(marked.json()["notification"]["read_at"])
        after = self.client.get("/api/notifications").json()
        updated = next(
            item for item in after["notifications"] if item["id"] == note["id"]
        )
        self.assertIsNotNone(updated["read_at"])
        self.assertEqual(after["unread_count"], body["unread_count"] - 1)

        cleared = self.client.post("/api/notifications/read-all")
        self.assertEqual(cleared.status_code, 200, cleared.text)
        cleared_body = cleared.json()
        self.assertEqual(cleared_body["unread_count"], 0)
        self.assertTrue(all(item["read_at"] for item in cleared_body["notifications"]))

    def test_health_reports_mock_backend(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["mock_ml"])
        self.assertEqual(payload["image_backend"], "mock")
        self.assertFalse(payload["demo_reset_allowed"])
        warmup = self.client.post("/api/health/warmup")
        self.assertEqual(warmup.status_code, 200)
        self.assertEqual(warmup.json()["state"], "mock")


if __name__ == "__main__":
    unittest.main()
