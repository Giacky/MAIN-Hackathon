"""Demo personas, paired sample photos, and location pins for a coherent walkthrough."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import zlib

from database.db import initialize_database
from database.repository import SQLiteRepository
from models.schemas import LocationGuess, Report, ReportType, User
from samples.presets import PRESETS
from services.auth import hash_password
from utils.config import DATABASE_PATH, UPLOAD_DIR, ensure_runtime_directories
from utils.images import save_upload_image

DEMO_PASSWORD = "demo"

# Report ids that tests and docs refer to by name.
DEMO_LOST_ID = "lost-demo-123"
DEMO_FOUND_LIBRARY_ID = "found-demo-456"
DEMO_FOUND_HOTEL_ID = "found-demo-789"
DEMO_LOST_EARBUDS_ID = "lost-demo-earbuds"
DEMO_FOUND_EARBUDS_ID = "found-demo-earbuds"

# Avatar palette shared with the web client.
AVATAR_TEAL = "#176B68"
AVATAR_CORAL = "#F28C68"
AVATAR_GREEN = "#4C956C"
AVATAR_CHARCOAL = "#202625"
AVATAR_PALETTE: tuple[str, ...] = (AVATAR_TEAL, AVATAR_CORAL, AVATAR_GREEN, AVATAR_CHARCOAL)

# Stable ids so sessions and seeded reports survive a reseed.
DEMO_ALEX_USER_ID = "user-demo-owner"
DEMO_SAM_USER_ID = "user-demo-finder"
DEMO_MIA_USER_ID = "user-demo-mia"
DEMO_NOOR_USER_ID = "user-demo-noor"

# Older names kept for callers and tests.
DEMO_OWNER_USER_ID = DEMO_ALEX_USER_ID
DEMO_FINDER_USER_ID = DEMO_SAM_USER_ID


@dataclass(frozen=True, slots=True)
class DemoAccount:
    user_id: str
    email: str
    display_name: str
    phone: str
    avatar: str
    summary: str


@dataclass(frozen=True, slots=True)
class DemoReportSpec:
    """One seeded report: which preset, who owns it, and how it is described."""

    report_id: str
    preset_id: str
    user_id: str
    hours_offset: int
    item: str
    prefer_anonymous: bool = False
    description: str | None = None
    holding_note: str | None = None


_PERSONAS: tuple[tuple[str, str, str, str, str], ...] = (
    # user_id, email, display_name, phone, avatar
    (DEMO_ALEX_USER_ID, "alex@demo.local", "Alex Janssen", "+31 6 1847 2210", AVATAR_TEAL),
    (DEMO_SAM_USER_ID, "sam@demo.local", "Sam de Vries", "+31 6 2501 7744", AVATAR_CORAL),
    (DEMO_MIA_USER_ID, "mia@demo.local", "Mia Chen", "+31 6 4291 8833", AVATAR_GREEN),
    (DEMO_NOOR_USER_ID, "noor@demo.local", "Noor Bakker", "+31 6 3376 9012", AVATAR_CHARCOAL),
)

# Lost/found pairs of the same item using the two different photos in samples/presets.py.
# event_time offsets run from -3 days to -1 hour so the time score varies per pair.
DEMO_REPORT_SPECS: tuple[DemoReportSpec, ...] = (
    # Wallet: Alex lost / Sam found (anonymous) / Mia found a brown one (distractor)
    DemoReportSpec(
        report_id=DEMO_LOST_ID,
        preset_id="lost_wallet",
        user_id=DEMO_ALEX_USER_ID,
        hours_offset=-6,
        item="a wallet",
        description="Black leather wallet. Lost in the library.",
    ),
    DemoReportSpec(
        report_id=DEMO_FOUND_LIBRARY_ID,
        preset_id="found_wallet",
        user_id=DEMO_SAM_USER_ID,
        hours_offset=-4,
        item="a wallet",
        prefer_anonymous=True,
        description="Black leather wallet found at the library entrance.",
        holding_note="Left at the library desk.",
    ),
    DemoReportSpec(
        report_id=DEMO_FOUND_HOTEL_ID,
        preset_id="found_brown",
        user_id=DEMO_MIA_USER_ID,
        hours_offset=-3,
        item="a card holder",
        description="Brown card holder left at hotel reception.",
        holding_note="At hotel reception.",
    ),
    # AirPods: Alex lost / Mia found
    DemoReportSpec(
        report_id=DEMO_LOST_EARBUDS_ID,
        preset_id="lost_earbuds",
        user_id=DEMO_ALEX_USER_ID,
        hours_offset=-2,
        item="AirPods",
        description="White AirPods case. Lost at the bus stop.",
    ),
    DemoReportSpec(
        report_id=DEMO_FOUND_EARBUDS_ID,
        preset_id="found_earbuds",
        user_id=DEMO_MIA_USER_ID,
        hours_offset=-1,
        item="AirPods",
        description="White AirPods case found next to the bus stop.",
        holding_note="I still have them.",
    ),
    # Keys: Sam lost / Alex found
    DemoReportSpec(
        report_id="lost-demo-keys",
        preset_id="lost_keys",
        user_id=DEMO_SAM_USER_ID,
        hours_offset=-30,
        item="keys",
    ),
    DemoReportSpec(
        report_id="found-demo-keys",
        preset_id="found_keys",
        user_id=DEMO_ALEX_USER_ID,
        hours_offset=-27,
        item="keys",
        holding_note="With me, can meet on campus.",
    ),
    # Glasses: Mia lost / Sam found (anonymous)
    DemoReportSpec(
        report_id="lost-demo-glasses",
        preset_id="lost_glasses",
        user_id=DEMO_MIA_USER_ID,
        hours_offset=-50,
        item="glasses",
    ),
    DemoReportSpec(
        report_id="found-demo-glasses",
        preset_id="found_glasses",
        user_id=DEMO_SAM_USER_ID,
        hours_offset=-46,
        item="glasses",
        prefer_anonymous=True,
        holding_note="Handed in at the library desk.",
    ),
    # Bottle: Sam lost / Mia found, plus a far Amsterdam distractor from Noor
    DemoReportSpec(
        report_id="lost-demo-bottle",
        preset_id="lost_bottle",
        user_id=DEMO_SAM_USER_ID,
        hours_offset=-72,
        item="a bottle",
    ),
    DemoReportSpec(
        report_id="found-demo-bottle",
        preset_id="found_bottle",
        user_id=DEMO_MIA_USER_ID,
        hours_offset=-70,
        item="a bottle",
        holding_note="In my bag.",
    ),
    DemoReportSpec(
        report_id="found-demo-bottle-far",
        preset_id="found_bottle_far",
        user_id=DEMO_NOOR_USER_ID,
        hours_offset=-24,
        item="a bottle",
        holding_note="Left on the park bench.",
    ),
    # Backpack: Noor lost / Alex found
    DemoReportSpec(
        report_id="lost-demo-backpack",
        preset_id="lost_backpack",
        user_id=DEMO_NOOR_USER_ID,
        hours_offset=-12,
        item="a backpack",
    ),
    DemoReportSpec(
        report_id="found-demo-backpack",
        preset_id="found_backpack",
        user_id=DEMO_ALEX_USER_ID,
        hours_offset=-9,
        item="a backpack",
        holding_note="Kept at home, can drop it off.",
    ),
    # Phone: Amsterdam mismatch (Sam)
    DemoReportSpec(
        report_id="found-demo-phone",
        preset_id="found_phone",
        user_id=DEMO_SAM_USER_ID,
        hours_offset=-36,
        item="a phone",
        holding_note="Gave it to the café staff.",
    ),
)

DEMO_REPORT_IDS: frozenset[str] = frozenset(spec.report_id for spec in DEMO_REPORT_SPECS)

PRESET_CATEGORIES = {
    "lost_wallet": "wallet",
    "found_wallet": "wallet",
    "found_brown": "wallet",
    "found_phone": "phone",
    "lost_keys": "keys",
    "found_keys": "keys",
    "lost_backpack": "bag",
    "found_backpack": "bag",
    "lost_bottle": "bottle",
    "found_bottle": "bottle",
    "found_bottle_far": "bottle",
    "lost_glasses": "glasses",
    "found_glasses": "glasses",
    "lost_earbuds": "earbuds",
    "found_earbuds": "earbuds",
}


def _join_items(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _summary_for(user_id: str) -> str:
    """Derive 'Lost a wallet and AirPods, found keys' from the seeded reports."""
    lost: list[str] = []
    found: list[str] = []
    for spec in DEMO_REPORT_SPECS:
        if spec.user_id != user_id:
            continue
        bucket = lost if PRESETS[spec.preset_id]["report_type"] == "lost" else found
        if spec.item not in bucket:
            bucket.append(spec.item)
    parts: list[str] = []
    if lost:
        parts.append(f"lost {_join_items(lost)}")
    if found:
        parts.append(f"found {_join_items(found)}")
    text = ", ".join(parts) or "no demo reports yet"
    return text[:1].upper() + text[1:]


DEMO_ACCOUNTS: tuple[DemoAccount, ...] = tuple(
    DemoAccount(
        user_id=user_id,
        email=email,
        display_name=display_name,
        phone=phone,
        avatar=avatar,
        summary=_summary_for(user_id),
    )
    for user_id, email, display_name, phone, avatar in _PERSONAS
)

_ACCOUNTS_BY_ID: dict[str, DemoAccount] = {account.user_id: account for account in DEMO_ACCOUNTS}


def demo_account_for_user(user_id: str | None) -> DemoAccount | None:
    if not user_id:
        return None
    return _ACCOUNTS_BY_ID.get(user_id)


def avatar_for_user(user_id: str | None) -> str:
    """Persona color for demo users; a deterministic palette pick for everyone else."""
    account = demo_account_for_user(user_id)
    if account is not None:
        return account.avatar
    digest = zlib.crc32((user_id or "").encode("utf-8"))
    return AVATAR_PALETTE[digest % len(AVATAR_PALETTE)]


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


def _ensure_user(repository: SQLiteRepository, account: DemoAccount) -> User:
    existing = repository.get_user(account.user_id) or repository.get_user_by_email(account.email)
    if existing:
        return existing
    return repository.add_user(
        User(
            id=account.user_id,
            email=account.email,
            display_name=account.display_name,
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


def _report_from_spec(spec: DemoReportSpec, owner: User, account: DemoAccount) -> Report:
    preset = PRESETS[spec.preset_id]
    latitude = float(preset["latitude"])
    longitude = float(preset["longitude"])
    radius = float(preset["radius_meters"])
    report = Report(
        id=spec.report_id,
        report_type=ReportType(preset["report_type"]),
        description=spec.description or preset["description"],
        category=PRESET_CATEGORIES.get(spec.preset_id),
        event_time=datetime.now(timezone.utc) + timedelta(hours=spec.hours_offset),
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius,
        locations=_location(latitude, longitude, radius),
        contact_email=owner.email,
        contact_phone=account.phone,
        prefer_anonymous=spec.prefer_anonymous,
        user_id=owner.id,
        holding_note=spec.holding_note,
    )
    report.image_paths = _copy_image(report.id, Path(preset["image"]))
    return report


def ensure_demo_data(
    repository: SQLiteRepository | None = None,
    *,
    prune_extras: bool = True,
) -> SQLiteRepository:
    """Create the demo personas and paired sample reports if they are missing.

    When prune_extras is True (the CLI reset default), non-demo reports are deleted.
    FastAPI startup passes prune_extras=False so user-created reports survive restarts.
    """
    ensure_runtime_directories()
    repository = repository or SQLiteRepository()
    users = {account.user_id: _ensure_user(repository, account) for account in DEMO_ACCOUNTS}
    for spec in DEMO_REPORT_SPECS:
        account = _ACCOUNTS_BY_ID[spec.user_id]
        _ensure_report(repository, _report_from_spec(spec, users[spec.user_id], account))
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
