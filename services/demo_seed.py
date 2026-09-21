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
from utils.images import save_prepared_image

DEMO_LOST_ID = "lost-demo-123"
DEMO_FOUND_LIBRARY_ID = "found-demo-456"
DEMO_FOUND_HOTEL_ID = "found-demo-789"
DEMO_LOST_KEYS_ID = "lost-demo-keys"
DEMO_FOUND_KEYS_ID = "found-demo-keys"
DEMO_FOUND_PHONE_ID = "found-demo-phone"
DEMO_LOST_BACKPACK_ID = "lost-demo-backpack"
DEMO_FOUND_BACKPACK_ID = "found-demo-backpack"
DEMO_LOST_BOTTLE_ID = "lost-demo-bottle"
DEMO_FOUND_BOTTLE_ID = "found-demo-bottle"
DEMO_FOUND_BOTTLE_FAR_ID = "found-demo-bottle-far"
DEMO_LOST_GLASSES_ID = "lost-demo-glasses"
DEMO_FOUND_GLASSES_ID = "found-demo-glasses"
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
    "lost_keys": "keys",
    "found_keys": "keys",
    "found_phone": "phone",
    "lost_backpack": "bag",
    "found_backpack": "bag",
    "lost_bottle": "bottle",
    "found_bottle": "bottle",
    "found_bottle_far": "bottle",
    "lost_glasses": "glasses",
    "found_glasses": "glasses",
    "lost_earbuds": "electronics",
    "found_earbuds": "electronics",
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
    destination = save_prepared_image(source, folder / "0.jpg")
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


def ensure_demo_data(repository: SQLiteRepository | None = None) -> SQLiteRepository:
    """Create dummy testers and sample reports if they are missing."""
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
            description=(
                "Small black leather wallet. I had my UM student card and a blue "
                "ING debit card in it. Last saw it on a desk in Inner City Library "
                "around closing time."
            ),
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_LIBRARY_ID,
            preset_id="found_wallet",
            user_id=sam.id,
            hours_offset=1,
            contact_email=sam.email,
            contact_phone=sam_phone,
            prefer_anonymous=True,
            description=(
                "Black leather wallet left on a table near the Inner City Library "
                "entrance. Cards still inside, looks like a student wallet."
            ),
            holding_note="Handed in at the Inner City Library information desk. Ask at the counter.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_HOTEL_ID,
            preset_id="found_brown",
            user_id=mia.id,
            hours_offset=2,
            contact_email=mia.email,
            contact_phone=mia_phone,
            prefer_anonymous=False,
            description=(
                "Brown bifold card holder a guest left on the hotel reception desk. "
                "Cash inside, no bank cards."
            ),
            holding_note="In the hotel lost-and-found box behind reception. Ask for Mia.",
        ),
        _report_from_preset(
            report_id=DEMO_LOST_KEYS_ID,
            preset_id="lost_keys",
            user_id=alex.id,
            hours_offset=0,
            contact_email=alex.email,
            contact_phone=alex_phone,
            prefer_anonymous=False,
            description=(
                "Three silver house keys on a blue plastic fob. I think they fell "
                "off my bag outside the Tapijn cafeteria."
            ),
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_KEYS_ID,
            preset_id="found_keys",
            user_id=sam.id,
            hours_offset=1,
            contact_email=sam.email,
            contact_phone=sam_phone,
            prefer_anonymous=True,
            description=(
                "Bunch of metal keys with a blue tag, sitting on a bench by the "
                "Tapijn cafeteria."
            ),
            holding_note="Left with cafeteria staff next to the till at Tapijn.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_PHONE_ID,
            preset_id="found_phone",
            user_id=mia.id,
            hours_offset=3,
            contact_email=mia.email,
            contact_phone=mia_phone,
            prefer_anonymous=False,
            description=(
                "Blue smartphone in a cracked case, left on a café table while I "
                "was in Amsterdam for the weekend."
            ),
            holding_note="I left it with the barista and told them someone might come by.",
        ),
        _report_from_preset(
            report_id=DEMO_LOST_BACKPACK_ID,
            preset_id="lost_backpack",
            user_id=alex.id,
            hours_offset=-8,
            contact_email=alex.email,
            contact_phone=alex_phone,
            prefer_anonymous=False,
            description=(
                "Old red student backpack with a laptop sleeve. I put it down at "
                "the Boschstraat bus stop and it was gone when the 1A came."
            ),
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_BACKPACK_ID,
            preset_id="found_backpack",
            user_id=sam.id,
            hours_offset=-7,
            contact_email=sam.email,
            contact_phone=sam_phone,
            prefer_anonymous=True,
            description=(
                "Worn red backpack with black zips, left on a bench at the bus stop "
                "near campus."
            ),
            holding_note="Dropped it at the bus-station service desk.",
        ),
        _report_from_preset(
            report_id=DEMO_LOST_BOTTLE_ID,
            preset_id="lost_bottle",
            user_id=alex.id,
            hours_offset=-6,
            contact_email=alex.email,
            contact_phone=alex_phone,
            prefer_anonymous=False,
            description=(
                "Dark green metal bottle covered in festival stickers. Last had it "
                "locked to my bike at the Vrijthof racks."
            ),
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_BOTTLE_ID,
            preset_id="found_bottle",
            user_id=sam.id,
            hours_offset=-5,
            contact_email=sam.email,
            contact_phone=sam_phone,
            prefer_anonymous=True,
            description=(
                "Green reusable metal bottle with travel stickers, next to the "
                "Vrijthof bike parking."
            ),
            holding_note="Left it at the bicycle-rental counter on Vrijthof.",
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_BOTTLE_FAR_ID,
            preset_id="found_bottle_far",
            user_id=mia.id,
            hours_offset=42,
            contact_email=mia.email,
            contact_phone=mia_phone,
            prefer_anonymous=False,
            description=(
                "Plain dark green insulated bottle with a black cap, on a path in "
                "Vondelpark while I was visiting a friend in Amsterdam."
            ),
            holding_note="Gave it to the park information kiosk.",
        ),
        _report_from_preset(
            report_id=DEMO_LOST_GLASSES_ID,
            preset_id="lost_glasses",
            user_id=alex.id,
            hours_offset=-4,
            contact_email=alex.email,
            contact_phone=alex_phone,
            prefer_anonymous=False,
            description=(
                "Black rectangular glasses in a blue hard case. I took them off in "
                "a study room at Inner City Library and forgot them under the desk."
            ),
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_GLASSES_ID,
            preset_id="found_glasses",
            user_id=sam.id,
            hours_offset=-3,
            contact_email=sam.email,
            contact_phone=sam_phone,
            prefer_anonymous=True,
            description=(
                "Black rectangular glasses and a dark blue case under a desk in "
                "Inner City Library."
            ),
            holding_note="At the Inner City Library information desk.",
        ),
        _report_from_preset(
            report_id=DEMO_LOST_EARBUDS_ID,
            preset_id="lost_earbuds",
            user_id=alex.id,
            hours_offset=-2,
            contact_email=alex.email,
            contact_phone=alex_phone,
            prefer_anonymous=False,
            description=(
                "Scratched white wireless-earbuds case. Probably dropped it getting "
                "on the bus at Boschstraat."
            ),
        ),
        _report_from_preset(
            report_id=DEMO_FOUND_EARBUDS_ID,
            preset_id="found_earbuds",
            user_id=mia.id,
            hours_offset=-1,
            contact_email=mia.email,
            contact_phone=mia_phone,
            prefer_anonymous=False,
            description=(
                "Dirty white earbuds charging case on the footpath by the campus "
                "bus stop. Picked it up after my evening shift."
            ),
            holding_note="I still have it. Happy to meet at the Boschstraat bus stop.",
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
