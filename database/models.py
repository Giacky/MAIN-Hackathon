"""Conversion helpers between SQLite rows and shared dataclasses."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from models.schemas import Report, ReportStatus, ReportType


def report_to_row(report: Report) -> dict[str, Any]:
    return {
        "id": report.id,
        "report_type": report.report_type.value,
        "description": report.description,
        "category": report.category,
        "urgency": report.urgency,
        "created_at": report.created_at.isoformat(),
        "event_time": report.event_time.isoformat() if report.event_time else None,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "radius_meters": report.radius_meters,
        "image_paths": json.dumps(report.image_paths),
        "status": report.status.value,
    }


def row_to_report(row: sqlite3.Row) -> Report:
    return Report(
        id=row["id"],
        report_type=ReportType(row["report_type"]),
        description=row["description"],
        category=row["category"],
        urgency=row["urgency"],
        created_at=datetime.fromisoformat(row["created_at"]),
        event_time=datetime.fromisoformat(row["event_time"])
        if row["event_time"]
        else None,
        latitude=row["latitude"],
        longitude=row["longitude"],
        radius_meters=row["radius_meters"],
        image_paths=tuple(json.loads(row["image_paths"])),
        status=ReportStatus(row["status"]),
    )
