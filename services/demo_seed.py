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
from utils.images import save_upload_image

DEMO_LOST_ID = "lost-demo-123"
DEMO_FOUND_LIBRARY_ID = "found-demo-456"
DEMO_FOUND_HOTEL_ID = "found-demo-789"
DEMO_LOST_EARBUDS_ID = "lost-demo-earbuds"
DEMO_FOUND_EARBUDS_ID = "found-demo-earbuds"
DEMO_PASSWORD = "demo"


@dataclass(frozen=True, slots=True)
class DemoAccount:
    user_id: str
    email: str
    display_name: str
    summary: str
    phone: str


DEMO_ACCOUNTS = (
    DemoAccount(
        user_id="user-demo-owner",
        email="alex@demo.local",
        display_name="Alex",
        summary="Lost items",
        phone="+31 6 1847 2210",
    ),
    DemoAccount(
        user_id="user-demo-finder",
        email="sam@demo.local",
        display_name="Sam",
        summary="Found items, stays anonymous",
        phone="+31 6 2501 7744",
    ),
    DemoAccount(
        user_id="user-demo-mia",
        email="mia@demo.local",
        display_name="Mia",
        summary="Found items",
        phone="+31 6 4291 8833",
    ),
)

DEMO_OWNER_USER_ID = DEMO_ACCOUNTS[0].user_id
DEMO_FINDER_USER_ID = DEMO_ACCOUNTS[1].user_id
DEMO_MIA_USER_ID = DEMO_ACCOUNTS[2].user_id

PRESET_CATEGORIES = {
    "lost_wallet": "wallet",
    "found_wallet": "wallet",
    "found_brown": "wallet",
    "lost_earbuds": "electronics",
    "found_earbuds": "electronics",
}

DEMO_REPORT_IDS = {
    DEMO_LOST_ID,
    DEMO_FOUND_LIBRARY_ID,
    DEMO_FOUND_HOTEL_ID,
    DEMO_LOST_EARBUDS_ID,
    DEMO_FOUND_EARBUDS_ID,
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
    destination = save_upload_image(source, folder / "0.jpg")
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
    if report.holding_note and existing.holding_note != report.holding_note:
        existing.holding_note = report.holding_note
        changed = True
    if existing.description != report.description:
        existing.description = report.description
        changed = True
    if existing.prefer_anonymous != report.prefer_anonymous:
        existing.prefer_anonymous = report.prefer_anonymous
        changed = True
    if existing.contact_phone != report.contact_phone:
        existing.contact_phone = report.contact_phone
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
    holding_note: str | None = None,
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
        holding_note=holding_note,
    )
    report.image_paths = _copy_image(report.id, Path(preset["image"]))
    return report


def ensure_demo_data(
    repository: SQLiteRepository | None = None,
    *,
    prune_extras: bool = True,
) -> SQLiteRepository:
    """Create dummy testers and sample reports if they are missing.

    When prune_extras is True (Streamlit default), non-demo reports are deleted.
    FastAPI startup should pass prune_extras=False so user-created reports survive restarts.
    """
    ensure_runtime_directories()
    repository = repository or SQLiteRepository()
    alex, sam, mia = (
        _ensure_user(repository, account.user_id, account.email, account.display_name)
        for account in DEMO_ACCOUNTS
    )

    alex_phone = DEMO_ACCOUNTS[0].phone
    sam_phone = DEMO_ACCOUNTS[1].phone
    mia_phone = DEMO_ACCOUNTS[2].phone
    specs = (
        _report_from_preset(
            report_id=DEMO_LOST_ID,
            preset_id="lost_wallet",
            user_id=alex.id,
            hours_offset=0,
            contact_email=alex.email,
            contact_phone=alex_phone,
            prefer_anonymous=False,
            description="Black leather wallet. Lost in the library.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_LIBRARY_ID,
            preset_id="found_wallet",
            user_id=sam.id,
            hours_offset=1,
            contact_email=sam.email,
            contact_phone=sam_phone,
            prefer_anonymous=True,
            description="Black leather wallet found at the library entrance.",
            holding_note="At the library desk.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_HOTEL_ID,
            preset_id="found_brown",
            user_id=mia.id,
            hours_offset=2,
            contact_email=mia.email,
            contact_phone=mia_phone,
            prefer_anonymous=False,
            description="Brown card holder left at hotel reception.",
            holding_note="At hotel reception.",
        ),
        _report_from_preset(
            report_id=DEMO_LOST_EARBUDS_ID,
            preset_id="lost_earbuds",
            user_id=alex.id,
            hours_offset=-2,
            contact_email=alex.email,
            contact_phone=alex_phone,
            prefer_anonymous=False,
            description="White AirPods case. Lost at the bus stop.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_EARBUDS_ID,
            preset_id="found_earbuds",
            user_id=mia.id,
            hours_offset=-1,
            contact_email=mia.email,
            contact_phone=mia_phone,
            prefer_anonymous=False,
            description="White AirPods case found next to the bus stop.",
            holding_note="I still have them.",
        ),
    )
    for report in specs:
        _ensure_report(repository, report)
    if prune_extras:
        _prune_extra_reports(repository)
    return repository


def _prune_extra_reports(repository: SQLiteRepository) -> None:
    """Drop leftover seed rows and duplicate uploads so the demo stays small."""
    for report in repository.list_reports():
        if report.id not in DEMO_REPORT_IDS:
            repository.delete_report(report.id)
    if UPLOAD_DIR.exists():
        for folder in UPLOAD_DIR.iterdir():
            if folder.is_dir() and folder.name not in DEMO_REPORT_IDS:
                shutil.rmtree(folder, ignore_errors=True)


def seed_demo_reports() -> tuple[list[Report], list[Report]]:
    """Wipe local data, then load the full demo (accounts + photos + pins)."""
    clear_database_and_uploads()
    repository = ensure_demo_data()
    reports = repository.list_reports()
    lost_reports = [item for item in reports if item.report_type == ReportType.LOST]
    found_reports = [item for item in reports if item.report_type == ReportType.FOUND]
    return lost_reports, found_reports
