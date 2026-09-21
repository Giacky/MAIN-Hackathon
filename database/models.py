"""Conversion helpers between SQLite rows and shared dataclasses."""

import json
import sqlite3
from datetime import datetime
from typing import Any

from models.schemas import (
    ChatMessage,
    Meetup,
    MeetupStatus,
    Report,
    ReportStatus,
    ReportType,
)


def _row_value(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    return row[key] if key in row.keys() else default


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
        "contact_email": report.contact_email,
        "contact_phone": report.contact_phone,
        "prefer_anonymous": int(report.prefer_anonymous),
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
        contact_email=_row_value(row, "contact_email"),
        contact_phone=_row_value(row, "contact_phone"),
        prefer_anonymous=bool(_row_value(row, "prefer_anonymous", 0)),
    )


def row_to_chat_message(row: sqlite3.Row) -> ChatMessage:
    return ChatMessage(
        id=row["id"],
        match_id=row["match_id"],
        sender=row["sender"],
        message=row["message"],
        timestamp=datetime.fromisoformat(row["timestamp"]),
    )


def meetup_to_row(meetup: Meetup) -> dict[str, Any]:
    return {
        "match_id": meetup.match_id,
        "id": meetup.id,
        "proposed_by": meetup.proposed_by,
        "location_name": meetup.location_name,
        "meeting_time": meetup.meeting_time.isoformat(),
        "status": meetup.status.value,
        "created_at": meetup.created_at.isoformat(),
    }


def row_to_meetup(row: sqlite3.Row) -> Meetup:
    return Meetup(
        match_id=row["match_id"],
        id=row["id"],
        proposed_by=row["proposed_by"],
        location_name=row["location_name"],
        meeting_time=datetime.fromisoformat(row["meeting_time"]),
        status=MeetupStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )
