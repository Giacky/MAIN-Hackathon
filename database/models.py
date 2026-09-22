"""Conversion helpers between SQLite rows and shared dataclasses."""

import json
import sqlite3
from datetime import datetime
from uuid import uuid4
from typing import Any

from models.schemas import (
    ChatMessage,
    LocationGuess,
    MatchResult,
    Meetup,
    MeetupStatus,
    Notification,
    Report,
    ReportStatus,
    ReportType,
    User,
    as_utc,
    utc_now,
)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return as_utc(datetime.fromisoformat(value))


def _isoformat_utc(value: datetime | None) -> str | None:
    aware = as_utc(value)
    return aware.isoformat() if aware else None


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
        "created_at": _isoformat_utc(report.created_at),
        "event_time": _isoformat_utc(report.event_time),
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
        "holding_note": report.holding_note,
    }


def row_to_report(row: sqlite3.Row) -> Report:
    return Report(
        id=row["id"],
        report_type=ReportType(row["report_type"]),
        description=row["description"],
        category=row["category"],
        urgency=row["urgency"],
        created_at=_parse_datetime(row["created_at"]) or utc_now(),
        event_time=_parse_datetime(row["event_time"]),
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
        holding_note=_row_value(row, "holding_note"),
    )


def row_to_match(row: sqlite3.Row) -> MatchResult:
    shortlisted = _row_value(row, "visual_shortlisted")
    return MatchResult(
        lost_report_id=row["lost_report_id"],
        found_report_id=row["found_report_id"],
        overall_score=row["overall_score"],
        text_score=row["text_score"],
        image_score=row["image_score"],
        geo_score=row["geo_score"],
        time_score=row["time_score"],
        distance_meters=row["distance_meters"],
        category_score=_row_value(row, "category_score"),
        image_error=_row_value(row, "image_error"),
        visual_shortlisted=(
            None if shortlisted is None else bool(shortlisted)
        ),
        visual_dino_score=_row_value(row, "visual_dino_score"),
        visual_inliers=_row_value(row, "visual_inliers"),
        visual_inlier_ratio=_row_value(row, "visual_inlier_ratio"),
    )


def row_to_chat_message(row: sqlite3.Row) -> ChatMessage:
    return ChatMessage(
        id=row["id"],
        match_id=row["match_id"],
        sender=row["sender"],
        message=row["message"],
        timestamp=_parse_datetime(row["timestamp"]) or utc_now(),
    )


def meetup_to_row(meetup: Meetup) -> dict[str, Any]:
    return {
        "match_id": meetup.match_id,
        "id": meetup.id,
        "proposed_by": meetup.proposed_by,
        "location_name": meetup.location_name,
        "meeting_time": _isoformat_utc(meetup.meeting_time),
        "status": meetup.status.value,
        "created_at": _isoformat_utc(meetup.created_at),
    }


def row_to_meetup(row: sqlite3.Row) -> Meetup:
    return Meetup(
        match_id=row["match_id"],
        id=row["id"],
        proposed_by=row["proposed_by"],
        location_name=row["location_name"],
        meeting_time=_parse_datetime(row["meeting_time"]) or utc_now(),
        status=MeetupStatus(row["status"]),
        created_at=_parse_datetime(row["created_at"]) or utc_now(),
    )


def user_to_row(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "password_hash": user.password_hash,
        "created_at": _isoformat_utc(user.created_at),
    }


def row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        password_hash=row["password_hash"],
        created_at=_parse_datetime(row["created_at"]) or utc_now(),
    )


def row_to_notification(row: sqlite3.Row) -> Notification:
    return Notification(
        id=row["id"],
        user_id=row["user_id"],
        kind=row["kind"],
        lost_report_id=row["lost_report_id"],
        found_report_id=row["found_report_id"],
        overall_score=row["overall_score"],
        created_at=_parse_datetime(row["created_at"]) or utc_now(),
        read_at=_parse_datetime(_row_value(row, "read_at")),
    )
