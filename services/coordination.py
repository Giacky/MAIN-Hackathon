"""Helpers for anonymous contact sharing and meetup coordination."""

from database.repository import SQLiteRepository
from models.schemas import Meetup, MeetupStatus, Report, ReportType

DEMO_LOST_ID = "lost-demo-123"
DEMO_FOUND_LIBRARY_ID = "found-demo-456"
DEMO_FOUND_HOTEL_ID = "found-demo-789"


def is_own_report(report: Report, viewer_role: str) -> bool:
    return (viewer_role == "lost" and report.report_type is ReportType.LOST) or (
        viewer_role == "found" and report.report_type is ReportType.FOUND
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


def ensure_demo_handoff_reports(repository: SQLiteRepository) -> None:
    """Insert the Matches-page demo pair so Recovery has real reports to coordinate."""
    if repository.get_report(DEMO_LOST_ID) is None:
        repository.add_report(
            Report(
                id=DEMO_LOST_ID,
                report_type=ReportType.LOST,
                description="I lost a small black wallet near the university library.",
                category="Wallet",
                latitude=50.8514,
                longitude=5.6900,
                radius_meters=500,
                contact_email="alex.owner@example.com",
                contact_phone=None,
                prefer_anonymous=False,
            )
        )
    if repository.get_report(DEMO_FOUND_LIBRARY_ID) is None:
        repository.add_report(
            Report(
                id=DEMO_FOUND_LIBRARY_ID,
                report_type=ReportType.FOUND,
                description="Black wallet found near the university library.",
                category="Wallet",
                latitude=50.8516,
                longitude=5.6902,
                radius_meters=200,
                contact_email="finder.library@example.com",
                contact_phone="+31 6 1234 5678",
                prefer_anonymous=True,
            )
        )
    if repository.get_report(DEMO_FOUND_HOTEL_ID) is None:
        repository.add_report(
            Report(
                id=DEMO_FOUND_HOTEL_ID,
                report_type=ReportType.FOUND,
                description="Dark card holder left at a hotel reception.",
                category="Wallet",
                latitude=50.8499,
                longitude=5.6880,
                radius_meters=300,
                contact_email="finder.hotel@example.com",
                contact_phone=None,
                prefer_anonymous=True,
            )
        )
