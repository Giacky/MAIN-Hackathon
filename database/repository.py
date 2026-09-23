"""Repository boundary and minimal SQLite implementation."""

from pathlib import Path
from typing import Protocol

from database.db import connection, initialize_database
from database.models import (
    meetup_to_row,
    report_to_row,
    row_to_chat_message,
    row_to_match,
    row_to_meetup,
    row_to_notification,
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
    Notification,
    Report,
    ReportStatus,
    User,
    utc_now,
)
from utils.config import DATABASE_PATH

_INACTIVE_STATUSES = {ReportStatus.RECOVERED.value, ReportStatus.CLOSED.value}


def _status_value(status: ReportStatus | str) -> str:
    if isinstance(status, ReportStatus):
        return status.value
    return str(status)


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
                    event_time, latitude, longitude, radius_meters, image_paths,
                    locations, status, contact_email, contact_phone, prefer_anonymous,
                    user_id, holding_note
                ) VALUES (
                    :id, :report_type, :description, :category, :urgency, :created_at,
                    :event_time, :latitude, :longitude, :radius_meters, :image_paths,
                    :locations, :status, :contact_email, :contact_phone,
                    :prefer_anonymous, :user_id, :holding_note
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

    def list_open_reports(self) -> list[Report]:
        return [
            report
            for report in self.list_reports()
            if _status_value(report.status) not in _INACTIVE_STATUSES
        ]

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

    def count_positive_matches_for_reports(
        self, report_ids: list[str]
    ) -> dict[str, int]:
        """Count positive, non-dismissed matches per report in one query."""
        if not report_ids:
            return {}
        placeholders = ",".join("?" * len(report_ids))
        with connection(self.database_path) as database:
            rows = database.execute(
                f"""
                SELECT report_id, COUNT(*) AS n FROM (
                    SELECT lost_report_id AS report_id
                    FROM matches
                    WHERE lost_report_id IN ({placeholders})
                      AND COALESCE(dismissed, 0) = 0
                      AND overall_score > 0
                    UNION ALL
                    SELECT found_report_id AS report_id
                    FROM matches
                    WHERE found_report_id IN ({placeholders})
                      AND COALESCE(dismissed, 0) = 0
                      AND overall_score > 0
                )
                GROUP BY report_id
                """,
                (*report_ids, *report_ids),
            ).fetchall()
        return {str(row["report_id"]): int(row["n"]) for row in rows}

    def delete_report(self, report_id: str) -> None:
        with connection(self.database_path) as database:
            database.execute("DELETE FROM reports WHERE id = ?", (report_id,))
            database.execute(
                """
                DELETE FROM matches
                WHERE lost_report_id = ? OR found_report_id = ?
                """,
                (report_id, report_id),
            )
            like_left = f"{report_id}:%"
            like_right = f"%:{report_id}"
            for table in ("meetups", "chat_messages", "drop_offs"):
                database.execute(
                    f"DELETE FROM {table} WHERE match_id LIKE ? OR match_id LIKE ?",
                    (like_left, like_right),
                )

    def mark_recovered(self, report_id: str) -> bool:
        return self.update_report_status(report_id, ReportStatus.RECOVERED)

    def update_report_status(self, report_id: str, status: ReportStatus) -> bool:
        with connection(self.database_path) as database:
            cursor = database.execute(
                "UPDATE reports SET status = ? WHERE id = ?",
                (status.value, report_id),
            )
        return cursor.rowcount > 0

    def save_match(self, match: MatchResult) -> MatchResult:
        shortlisted = match.visual_shortlisted
        same_object = match.visual_same_object
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO matches (
                    lost_report_id, found_report_id, overall_score, text_score,
                    image_score, geo_score, time_score, distance_meters,
                    category_score, image_error, visual_shortlisted,
                    visual_dino_score, visual_inliers, visual_inlier_ratio,
                    visual_same_object
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(lost_report_id, found_report_id) DO UPDATE SET
                    overall_score = excluded.overall_score,
                    text_score = excluded.text_score,
                    image_score = excluded.image_score,
                    geo_score = excluded.geo_score,
                    time_score = excluded.time_score,
                    distance_meters = excluded.distance_meters,
                    category_score = excluded.category_score,
                    image_error = excluded.image_error,
                    visual_shortlisted = excluded.visual_shortlisted,
                    visual_dino_score = excluded.visual_dino_score,
                    visual_inliers = excluded.visual_inliers,
                    visual_inlier_ratio = excluded.visual_inlier_ratio,
                    visual_same_object = excluded.visual_same_object
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
                    match.category_score,
                    match.image_error,
                    None if shortlisted is None else int(bool(shortlisted)),
                    match.visual_dino_score,
                    match.visual_inliers,
                    match.visual_inlier_ratio,
                    None if same_object is None else int(bool(same_object)),
                ),
            )
        return match

    def list_matches(self) -> list[MatchResult]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT * FROM matches
                ORDER BY overall_score DESC
                """
            ).fetchall()
        return [row_to_match(row) for row in rows]

    def list_matches_for_report(self, report_id: str) -> list[MatchResult]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT * FROM matches
                WHERE (lost_report_id = ? OR found_report_id = ?)
                  AND COALESCE(dismissed, 0) = 0
                ORDER BY overall_score DESC
                """,
                (report_id, report_id),
            ).fetchall()
        return [row_to_match(row) for row in rows]

    def get_match(self, lost_report_id: str, found_report_id: str) -> MatchResult | None:
        with connection(self.database_path) as database:
            row = database.execute(
                """
                SELECT * FROM matches
                WHERE lost_report_id = ? AND found_report_id = ?
                """,
                (lost_report_id, found_report_id),
            ).fetchone()
        return row_to_match(row) if row else None

    def dismiss_match(self, lost_report_id: str, found_report_id: str) -> bool:
        with connection(self.database_path) as database:
            cursor = database.execute(
                """
                UPDATE matches
                SET dismissed = 1
                WHERE lost_report_id = ? AND found_report_id = ?
                """,
                (lost_report_id, found_report_id),
            )
        return cursor.rowcount > 0

    def undismiss_match(self, lost_report_id: str, found_report_id: str) -> bool:
        with connection(self.database_path) as database:
            cursor = database.execute(
                """
                UPDATE matches
                SET dismissed = 0
                WHERE lost_report_id = ? AND found_report_id = ?
                """,
                (lost_report_id, found_report_id),
            )
        return cursor.rowcount > 0

    def create_match_notification(
        self,
        *,
        user_id: str,
        lost_report_id: str,
        found_report_id: str,
        overall_score: float,
    ) -> None:
        notification = Notification(
            user_id=user_id,
            kind="match",
            lost_report_id=lost_report_id,
            found_report_id=found_report_id,
            overall_score=overall_score,
        )
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT OR IGNORE INTO notifications (
                    id, user_id, kind, lost_report_id, found_report_id,
                    overall_score, created_at, read_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification.id,
                    notification.user_id,
                    notification.kind,
                    notification.lost_report_id,
                    notification.found_report_id,
                    notification.overall_score,
                    notification.created_at.isoformat(),
                    None,
                ),
            )

    def list_notifications(self, user_id: str) -> list[Notification]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT * FROM notifications
                WHERE user_id = ?
                ORDER BY CASE WHEN read_at IS NULL THEN 0 ELSE 1 END,
                         created_at DESC
                """,
                (user_id,),
            ).fetchall()
        return [row_to_notification(row) for row in rows]

    def count_unread_notifications(self, user_id: str) -> int:
        with connection(self.database_path) as database:
            row = database.execute(
                """
                SELECT COUNT(*) AS n FROM notifications
                WHERE user_id = ? AND read_at IS NULL
                """,
                (user_id,),
            ).fetchone()
        return int(row["n"] if row is not None else 0)

    def mark_notification_read(
        self, notification_id: str, user_id: str
    ) -> Notification | None:
        now = utc_now().isoformat()
        with connection(self.database_path) as database:
            database.execute(
                """
                UPDATE notifications
                SET read_at = ?
                WHERE id = ? AND user_id = ? AND read_at IS NULL
                """,
                (now, notification_id, user_id),
            )
            row = database.execute(
                """
                SELECT * FROM notifications
                WHERE id = ? AND user_id = ?
                """,
                (notification_id, user_id),
            ).fetchone()
        return row_to_notification(row) if row else None

    def mark_all_notifications_read(self, user_id: str) -> int:
        now = utc_now().isoformat()
        with connection(self.database_path) as database:
            cursor = database.execute(
                """
                UPDATE notifications
                SET read_at = ?
                WHERE user_id = ? AND read_at IS NULL
                """,
                (now, user_id),
            )
        return cursor.rowcount

    def create_message_notification(
        self,
        *,
        user_id: str,
        lost_report_id: str,
        found_report_id: str,
    ) -> None:
        """One unread alert per chat message (kind=message; not unique per pair)."""
        notification = Notification(
            user_id=user_id,
            kind="message",
            lost_report_id=lost_report_id,
            found_report_id=found_report_id,
            overall_score=0.0,
        )
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO notifications (
                    id, user_id, kind, lost_report_id, found_report_id,
                    overall_score, created_at, read_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    notification.id,
                    notification.user_id,
                    notification.kind,
                    notification.lost_report_id,
                    notification.found_report_id,
                    notification.overall_score,
                    notification.created_at.isoformat(),
                    None,
                ),
            )

    def save_push_subscription(
        self,
        *,
        user_id: str,
        endpoint: str,
        p256dh: str,
        auth: str,
    ) -> None:
        now = utc_now().isoformat()
        with connection(self.database_path) as database:
            database.execute(
                """
                INSERT INTO push_subscriptions (endpoint, user_id, p256dh, auth, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(endpoint) DO UPDATE SET
                    user_id = excluded.user_id,
                    p256dh = excluded.p256dh,
                    auth = excluded.auth,
                    created_at = excluded.created_at
                """,
                (endpoint, user_id, p256dh, auth, now),
            )

    def delete_push_subscription(self, *, user_id: str, endpoint: str) -> bool:
        with connection(self.database_path) as database:
            cursor = database.execute(
                """
                DELETE FROM push_subscriptions
                WHERE user_id = ? AND endpoint = ?
                """,
                (user_id, endpoint),
            )
        return cursor.rowcount > 0

    def list_push_subscriptions(self, user_id: str) -> list[dict[str, str]]:
        with connection(self.database_path) as database:
            rows = database.execute(
                """
                SELECT endpoint, p256dh, auth FROM push_subscriptions
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchall()
        return [
            {
                "endpoint": row["endpoint"],
                "p256dh": row["p256dh"],
                "auth": row["auth"],
            }
            for row in rows
        ]

    def delete_push_endpoint(self, endpoint: str) -> None:
        with connection(self.database_path) as database:
            database.execute(
                "DELETE FROM push_subscriptions WHERE endpoint = ?",
                (endpoint,),
            )

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
