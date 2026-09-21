"""Conversion helpers between SQLite rows and shared dataclasses."""

import json
import sqlite3
from datetime import datetime
from uuid import uuid4
from typing import Any

from models.schemas import LocationGuess, Report, ReportStatus, ReportType


def _locations_from_row(row: sqlite3.Row) -> tuple[LocationGuess, ...]:
    keys = row.keys()
    raw = row["locations"] if "locations" in keys and row["locations"] else "[]"
    payload = json.loads(raw)
    return tuple(
        LocationGuess(
            id=item.get("id") or str(uuid4()),
            latitude=item["latitude"],
            longitude=item["longitude"],
            radius_meters=float(item.get("radius_meters", 200)),
        )
        for item in payload
    )


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
        "locations": json.dumps(
            [
                {
                    "id": location.id,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "radius_meters": location.radius_meters,
                }
                for location in report.locations
            ]
        ),
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
        locations=_locations_from_row(row),
        image_paths=tuple(json.loads(row["image_paths"])),
        status=ReportStatus(row["status"]),
    )
