"""Conversion helpers between SQLite rows and shared dataclasses."""

import json
import sqlite3
from datetime import datetime
from uuid import uuid4
from typing import Any

from models.schemas import (
    ChatMessage,
    LocationGuess,
    Meetup,
    MeetupStatus,
    Report,
    ReportStatus,
    ReportType,
    User,
)


def _row_value(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    return row[key] if key in row.keys() else default


def _locations_from_row(row: sqlite3.Row) -> tuple[LocationGuess, ...]:
    raw = _row_value(row, "locations") or "[]"
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
        "contact_email": report.contact_email,
        "contact_phone": report.contact_phone,
        "prefer_anonymous": int(report.prefer_anonymous),
        "user_id": report.user_id,
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
        contact_email=_row_value(row, "contact_email"),
        contact_phone=_row_value(row, "contact_phone"),
        prefer_anonymous=bool(_row_value(row, "prefer_anonymous", 0)),
        user_id=_row_value(row, "user_id"),
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


def user_to_row(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "password_hash": user.password_hash,
        "created_at": user.created_at.isoformat(),
    }


def row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        password_hash=row["password_hash"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
