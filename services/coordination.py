"""Helpers for anonymous contact sharing and meetup coordination."""

from database.repository import SQLiteRepository
from models.schemas import Meetup, MeetupStatus, Report, ReportType
from services.demo_seed import (
    DEMO_ACCOUNTS,
    DEMO_FINDER_USER_ID,
    DEMO_FOUND_HOTEL_ID,
    DEMO_FOUND_LIBRARY_ID,
    DEMO_LOST_ID,
    DEMO_MIA_USER_ID,
    DEMO_OWNER_USER_ID,
    DEMO_PASSWORD,
    ensure_demo_data,
)

__all__ = [
    "DEMO_ACCOUNTS",
    "DEMO_FINDER_USER_ID",
    "DEMO_FOUND_HOTEL_ID",
    "DEMO_FOUND_LIBRARY_ID",
    "DEMO_LOST_ID",
    "DEMO_MIA_USER_ID",
    "DEMO_OWNER_USER_ID",
    "DEMO_PASSWORD",
    "can_respond_to_meetup",
    "contact_for_viewer",
    "display_name_for_sender",
    "ensure_demo_handoff_reports",
    "is_own_report",
    "role_for_user",
]


def is_own_report(report: Report, viewer_role: str) -> bool:
    return (viewer_role == "lost" and report.report_type == ReportType.LOST) or (
        viewer_role == "found" and report.report_type == ReportType.FOUND
    )


def contact_for_viewer(report: Report, viewer_role: str) -> tuple[str | None, str | None]:
    """Hide email/phone from the other person when the reporter asked to stay anonymous."""
    if is_own_report(report, viewer_role) or not report.prefer_anonymous:
        return report.contact_email, report.contact_phone
    return None, None


def display_name_for_sender(sender: str, viewer_role: str) -> str:
    if sender == viewer_role:
        return "You"
    if sender == "found":
        return "Finder"
    return "Owner"


def can_respond_to_meetup(meetup: Meetup, viewer_role: str) -> bool:
    """Only the other person can accept or decline a proposal."""
    return meetup.proposed_by != viewer_role and meetup.status is MeetupStatus.PROPOSED


def role_for_user(
    user_id: str | None,
    lost: Report,
    found: Report,
    email: str | None = None,
) -> str | None:
    """Infer owner vs finder from which report belongs to the logged-in user."""
    if user_id:
        if lost.user_id == user_id:
            return "lost"
        if found.user_id == user_id:
            return "found"
    if email:
        lowered = email.strip().lower()
        if (lost.contact_email or "").strip().lower() == lowered:
            return "lost"
        if (found.contact_email or "").strip().lower() == lowered:
            return "found"
    return None


def ensure_demo_handoff_reports(repository: SQLiteRepository) -> None:
    """Insert dummy testers and sample reports if they are missing."""
    ensure_demo_data(repository)
