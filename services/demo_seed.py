"""Reset SQLite + uploads and seed a clean demo dataset.

Default demo set: 2 lost reports and 4 found reports.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil

from database.db import initialize_database
from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from samples.presets import PRESETS
from utils.config import DATABASE_PATH, UPLOAD_DIR, ensure_runtime_directories

DEMO_LOST = ("lost_wallet", "lost_keys")
DEMO_FOUND = ("found_wallet", "found_brown", "found_keys", "found_phone")


def clear_database_and_uploads() -> None:
    ensure_runtime_directories()
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    if UPLOAD_DIR.exists():
        shutil.rmtree(UPLOAD_DIR)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    initialize_database(DATABASE_PATH)


def _seed_one(repository: SQLiteRepository, preset_id: str, hours_offset: int) -> Report:
    preset = PRESETS[preset_id]
    report = Report(
        report_type=ReportType(preset["report_type"]),
        description=preset["description"],
        event_time=datetime.now(timezone.utc) + timedelta(hours=hours_offset),
        latitude=float(preset["latitude"]),
        longitude=float(preset["longitude"]),
        radius_meters=float(preset["radius_meters"]),
    )
    source = Path(preset["image"])
    if source.is_file():
        folder = UPLOAD_DIR / report.id
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"0{source.suffix.lower() or '.png'}"
        shutil.copy2(source, destination)
        report.image_paths = (str(destination),)
    return repository.add_report(report)


def seed_demo_reports() -> tuple[list[Report], list[Report]]:
    """Wipe DB, then insert exactly 2 lost and 4 found sample reports."""
    clear_database_and_uploads()
    repository = SQLiteRepository()
    lost_reports = [
        _seed_one(repository, preset_id, hours_offset=0) for preset_id in DEMO_LOST
    ]
    found_reports = [
        _seed_one(repository, preset_id, hours_offset=index + 1)
        for index, preset_id in enumerate(DEMO_FOUND)
    ]
    return lost_reports, found_reports
