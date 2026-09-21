"""Repository boundary and minimal SQLite implementation."""

from pathlib import Path
from typing import Protocol

from database.db import connection, initialize_database
from database.models import (
    meetup_to_row,
    report_to_row,
    row_to_chat_message,
    row_to_meetup,
    row_to_report,
    row_to_user,
    user_to_row,
)
from models.schemas import (
    ChatMessage,
    DropOff,
    MatchResult,
    Meetup,
    MeetupStatus,
    Report,
    ReportStatus,
    User,
)
from utils.config import DATABASE_PATH


class ReportRepository(Protocol):
    """Minimum persistence interface the UI can depend on."""

    def add_report(self, report: Report) -> Report: ...

    def get_report(self, report_id: str) -> Report | None: ...

    def list_reports(self) -> list[Report]: ...

    def mark_recovered(self, report_id: str) -> bool: ...


class SQLiteRepository:
    """Small SQLite store; intentionally avoids an ORM and migrations."""

    def __init__(self, database_path: Path = DATABASE_PATH) -> None:
        self.database_path = database_path
        initialize_database(database_path)

    def add_report(self, report: Report) -> Report:
        values = report_to_row(report)
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT OR REPLACE INTO reports (
                    id, report_type, description, category, urgency, created_at,
                    event_time, latitude, longitude, radius_meters, image_paths, status,
                    contact_email, contact_phone, prefer_anonymous, user_id
                ) VALUES (
                    :id, :report_type, :description, :category, :urgency, :created_at,
                    :event_time, :latitude, :longitude, :radius_meters, :image_paths, :status,
                    :contact_email, :contact_phone, :prefer_anonymous, :user_id
                )
                """,
                values,
            )
        return report

    def get_report(self, report_id: str) -> Report | None:
        with connection(self.database_path) as database:
            row = database.execute(
                "SELECT * FROM reports WHERE id = ?", (report_id,)
            ).fetchone()
        return row_to_report(row) if row else None

    def list_reports(self) -> list[Report]:
        with connection(self.database_path) as database:
            rows = database.execute(
                "SELECT * FROM reports ORDER BY created_at DESC"
            ).fetchall()
        return [row_to_report(row) for row in rows]

    def list_reports_for_user(self, user_id: str) -> list[Report]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT * FROM reports
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [row_to_report(row) for row in rows]

    def mark_recovered(self, report_id: str) -> bool:
        with connection(self.database_path) as database:
            cursor = database.execute(
                "UPDATE reports SET status = ? WHERE id = ?",
                (ReportStatus.RECOVERED.value, report_id),
            )
        return cursor.rowcount > 0

    def save_match(self, match: MatchResult) -> MatchResult:
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT OR REPLACE INTO matches VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match.lost_report_id,
                    match.found_report_id,
                    match.overall_score,
                    match.text_score,
                    match.image_score,
                    match.geo_score,
                    match.time_score,
                    match.distance_meters,
                ),
            )
        return match

    def add_chat_message(self, message: ChatMessage) -> ChatMessage:
        with connection(self.database_path) as database:
            database.execute(
                "INSERT INTO chat_messages VALUES (?, ?, ?, ?, ?)",
                (
                    message.id,
                    message.match_id,
                    message.sender,
                    message.message,
                    message.timestamp.isoformat(),
                ),
            )
        return message

    def list_chat_messages(self, match_id: str) -> list[ChatMessage]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT * FROM chat_messages
                WHERE match_id = ?
                ORDER BY timestamp ASC
                """,
                (match_id,),
            ).fetchall()
        return [row_to_chat_message(row) for row in rows]

    def add_drop_off(self, drop_off: DropOff) -> DropOff:
        with connection(self.database_path) as database:
            database.execute(
                "INSERT OR REPLACE INTO drop_offs VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    drop_off.id,
                    drop_off.match_id,
                    drop_off.name,
                    drop_off.latitude,
                    drop_off.longitude,
                    drop_off.instructions,
                    drop_off.timestamp.isoformat(),
                ),
            )
        return drop_off

    def get_meetup(self, match_id: str) -> Meetup | None:
        with connection(self.database_path) as database:
            row = database.execute(
                "SELECT * FROM meetups WHERE match_id = ?", (match_id,)
            ).fetchone()
        return row_to_meetup(row) if row else None

    def save_meetup(self, meetup: Meetup) -> Meetup:
        values = meetup_to_row(meetup)
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT OR REPLACE INTO meetups (
                    match_id, id, proposed_by, location_name, meeting_time, status, created_at
                ) VALUES (
                    :match_id, :id, :proposed_by, :location_name, :meeting_time, :status, :created_at
                )
                """,
                values,
            )
        return meetup

    def update_meetup_status(self, match_id: str, status: MeetupStatus) -> bool:
        with connection(self.database_path) as database:
            cursor = database.execute(
                "UPDATE meetups SET status = ? WHERE match_id = ?",
                (status.value, match_id),
            )
        return cursor.rowcount > 0

    def add_user(self, user: User) -> User:
        values = user_to_row(user)
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO users (id, email, display_name, password_hash, created_at)
                VALUES (:id, :email, :display_name, :password_hash, :created_at)
                """,
                values,
            )
        return user

    def get_user(self, user_id: str) -> User | None:
        with connection(self.database_path) as database:
            row = database.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return row_to_user(row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        with connection(self.database_path) as database:
            row = database.execute(
                "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
        return row_to_user(row) if row else None
