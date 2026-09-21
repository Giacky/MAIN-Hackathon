"""Demo users, sample photos, and location pins for a coherent walkthrough."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass
import shutil

from database.db import initialize_database
from database.repository import SQLiteRepository
from models.schemas import LocationGuess, Report, ReportType, User
from samples.presets import PRESETS
from services.auth import hash_password
from utils.config import DATABASE_PATH, UPLOAD_DIR, ensure_runtime_directories

DEMO_LOST_ID = "lost-demo-123"
DEMO_FOUND_LIBRARY_ID = "found-demo-456"
DEMO_FOUND_HOTEL_ID = "found-demo-789"
DEMO_LOST_KEYS_ID = "lost-demo-keys"
DEMO_FOUND_KEYS_ID = "found-demo-keys"
DEMO_FOUND_PHONE_ID = "found-demo-phone"
DEMO_PASSWORD = "demo"


@dataclass(frozen=True, slots=True)
class DemoAccount:
    user_id: str
    email: str
    display_name: str
    summary: str


DEMO_ACCOUNTS = (
    DemoAccount(
        user_id="user-demo-owner",
        email="alex@demo.local",
        display_name="Alex",
        summary="Lost a black wallet. Shares contact.",
    ),
    DemoAccount(
        user_id="user-demo-finder",
        email="sam@demo.local",
        display_name="Sam",
        summary="Found a wallet at the library. Stays anonymous.",
    ),
    DemoAccount(
        user_id="user-demo-mia",
        email="mia@demo.local",
        display_name="Mia",
        summary="Found a card holder at a hotel. Shares a phone number.",
    ),
)

DEMO_OWNER_USER_ID = DEMO_ACCOUNTS[0].user_id
DEMO_FINDER_USER_ID = DEMO_ACCOUNTS[1].user_id
DEMO_MIA_USER_ID = DEMO_ACCOUNTS[2].user_id

PRESET_CATEGORIES = {
    "lost_wallet": "wallet",
    "found_wallet": "wallet",
    "found_brown": "wallet",
    "lost_keys": "keys",
    "found_keys": "keys",
    "found_phone": "phone",
}


def clear_database_and_uploads() -> None:
    ensure_runtime_directories()
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    initialize_database(DATABASE_PATH)


def _copy_image(report_id: str, source: Path) -> tuple[str, ...]:
    if not source.is_file():
        return ()
    folder = UPLOAD_DIR / report_id
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"0{source.suffix.lower() or '.png'}"
    shutil.copy2(source, destination)
    return (str(destination),)


def _location(latitude: float, longitude: float, radius_meters: float) -> tuple[LocationGuess, ...]:
    return (
        LocationGuess(
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
        ),
    )


def _ensure_user(repository: SQLiteRepository, user_id: str, email: str, display_name: str) -> User:
    existing = repository.get_user(user_id) or repository.get_user_by_email(email)
    if existing:
        return existing
    return repository.add_user(
        User(
            id=user_id,
            email=email,
            display_name=display_name,
            password_hash=hash_password(DEMO_PASSWORD),
        )
    )


def _ensure_report(repository: SQLiteRepository, report: Report) -> Report:
    existing = repository.get_report(report.id)
    if existing is None:
        return repository.add_report(report)
    changed = False
    if existing.user_id != report.user_id:
        existing.user_id = report.user_id
        changed = True
    if not existing.locations and report.locations:
        existing.locations = report.locations
        existing.latitude = report.latitude
        existing.longitude = report.longitude
        existing.radius_meters = report.radius_meters
        changed = True
    if not existing.image_paths and report.image_paths:
        existing.image_paths = report.image_paths
        changed = True
    if changed:
        return repository.add_report(existing)
    return existing


def _report_from_preset(
    *,
    report_id: str,
    preset_id: str,
    user_id: str,
    hours_offset: int,
    contact_email: str,
    contact_phone: str,
    prefer_anonymous: bool,
    description: str | None = None,
) -> Report:
    preset = PRESETS[preset_id]
    latitude = float(preset["latitude"])
    longitude = float(preset["longitude"])
    radius = float(preset["radius_meters"])
    report = Report(
        id=report_id,
        report_type=ReportType(preset["report_type"]),
        description=description or preset["description"],
        category=PRESET_CATEGORIES.get(preset_id),
        event_time=datetime.now(timezone.utc) + timedelta(hours=hours_offset),
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius,
        locations=_location(latitude, longitude, radius),
        contact_email=contact_email,
        contact_phone=contact_phone,
        prefer_anonymous=prefer_anonymous,
        user_id=user_id,
    )
    report.image_paths = _copy_image(report.id, Path(preset["image"]))
    return report


def ensure_demo_data(repository: SQLiteRepository | None = None) -> SQLiteRepository:
    """Create dummy testers and sample reports if they are missing."""
    ensure_runtime_directories()
    repository = repository or SQLiteRepository()
    alex, sam, mia = (
        _ensure_user(repository, account.user_id, account.email, account.display_name)
        for account in DEMO_ACCOUNTS
    )

    specs = (
        _report_from_preset(
            report_id=DEMO_LOST_ID,
            preset_id="lost_wallet",
            user_id=alex.id,
            hours_offset=0,
            contact_email=alex.email,
            contact_phone="+31 6 1111 1111",
            prefer_anonymous=False,
            description="I lost a small black wallet near the university library.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_LIBRARY_ID,
            preset_id="found_wallet",
            user_id=sam.id,
            hours_offset=1,
            contact_email=sam.email,
            contact_phone="+31 6 2222 2222",
            prefer_anonymous=True,
            description="Black wallet found near the university library.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_HOTEL_ID,
            preset_id="found_brown",
            user_id=mia.id,
            hours_offset=2,
            contact_email=mia.email,
            contact_phone="+31 6 3333 3333",
            prefer_anonymous=False,
            description="Dark card holder left at a hotel reception.",
        ),
        _report_from_preset(
            report_id=DEMO_LOST_KEYS_ID,
            preset_id="lost_keys",
            user_id=alex.id,
            hours_offset=0,
            contact_email=alex.email,
            contact_phone="+31 6 1111 1111",
            prefer_anonymous=False,
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_KEYS_ID,
            preset_id="found_keys",
            user_id=sam.id,
            hours_offset=1,
            contact_email=sam.email,
            contact_phone="+31 6 2222 2222",
            prefer_anonymous=True,
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_PHONE_ID,
            preset_id="found_phone",
            user_id=mia.id,
            hours_offset=3,
            contact_email=mia.email,
            contact_phone="+31 6 3333 3333",
            prefer_anonymous=False,
        ),
    )
    for report in specs:
        _ensure_report(repository, report)
    return repository


def seed_demo_reports() -> tuple[list[Report], list[Report]]:
    """Wipe local data, then load the full demo (accounts + photos + pins)."""
    clear_database_and_uploads()
    repository = ensure_demo_data()
    reports = repository.list_reports()
    lost_reports = [item for item in reports if item.report_type == ReportType.LOST]
    found_reports = [item for item in reports if item.report_type == ReportType.FOUND]
    return lost_reports, found_reports
