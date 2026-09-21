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
    DEMO_FOUND_LIBRARY_ID,
    DEMO_LOST_ID,
    DEMO_PASSWORD,
    ensure_demo_data,
)
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
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

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

    def test_create_multipart_report_and_safe_image_url(self) -> None:
        self._login("alex@demo.local")
        image = Image.new("RGB", (1600, 900), color=(20, 40, 60))
        buffer = BytesIO()
        image.save(buffer, format="JPEG")
        buffer.seek(0)
        locations = json.dumps(
            [{"latitude": 50.85, "longitude": 5.69, "radius_meters": 200}]
        )
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
        self.assertEqual(response.status_code, 200, response.text)
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
        response = self.client.get(f"/api/matches?report_id={DEMO_LOST_ID}")
        self.assertEqual(response.status_code, 200, response.text)
        matches = response.json()["matches"]
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

    def test_health_reports_mock_backend(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["mock_ml"])
        self.assertEqual(payload["image_backend"], "mock")
        warmup = self.client.post("/api/health/warmup")
        self.assertEqual(warmup.status_code, 200)
        self.assertEqual(warmup.json()["state"], "mock")


if __name__ == "__main__":
    unittest.main()
