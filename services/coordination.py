"""Helpers for anonymous contact sharing and meetup coordination."""

from dataclasses import dataclass

from database.repository import SQLiteRepository
from models.schemas import Meetup, MeetupStatus, Report, ReportType, User
from services.auth import hash_password

DEMO_LOST_ID = "lost-demo-123"
DEMO_FOUND_LIBRARY_ID = "found-demo-456"
DEMO_FOUND_HOTEL_ID = "found-demo-789"
DEMO_PASSWORD = "demo"


@dataclass(frozen=True, slots=True)
class DemoAccount:
    user_id: str
    email: str
    display_name: str
    summary: str


DEMO_ACCOUNTS = (
    DemoAccount(
        user_id="user-demo-owner",
        email="alex@demo.local",
        display_name="Alex",
        summary="Lost a black wallet. Shares contact.",
    ),
    DemoAccount(
        user_id="user-demo-finder",
        email="sam@demo.local",
        display_name="Sam",
        summary="Found a wallet at the library. Stays anonymous.",
    ),
    DemoAccount(
        user_id="user-demo-mia",
        email="mia@demo.local",
        display_name="Mia",
        summary="Found a card holder at a hotel. Shares a phone number.",
    ),
)

DEMO_OWNER_USER_ID = DEMO_ACCOUNTS[0].user_id
DEMO_FINDER_USER_ID = DEMO_ACCOUNTS[1].user_id
DEMO_MIA_USER_ID = DEMO_ACCOUNTS[2].user_id
DEMO_OWNER_EMAIL = DEMO_ACCOUNTS[0].email
DEMO_FINDER_EMAIL = DEMO_ACCOUNTS[1].email
DEMO_MIA_EMAIL = DEMO_ACCOUNTS[2].email


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


def _ensure_user(
    repository: SQLiteRepository,
    user_id: str,
    email: str,
    display_name: str,
) -> User:
    existing = repository.get_user(user_id) or repository.get_user_by_email(email)
    if existing:
        return existing
    return repository.add_user(
        User(
            id=user_id,
            email=email,
            display_name=display_name,
            password_hash=hash_password(DEMO_PASSWORD),
        )
    )


def _assign_report(repository: SQLiteRepository, report: Report, user: User) -> None:
    if report.user_id != user.id:
        report.user_id = user.id
        repository.add_report(report)


def ensure_demo_handoff_reports(repository: SQLiteRepository) -> None:
    """Insert three dummy accounts and their reports for local testing."""
    alex, sam, mia = (
        _ensure_user(repository, account.user_id, account.email, account.display_name)
        for account in DEMO_ACCOUNTS
    )

    lost = repository.get_report(DEMO_LOST_ID)
    if lost is None:
        repository.add_report(
            Report(
                id=DEMO_LOST_ID,
                report_type=ReportType.LOST,
                description="I lost a small black wallet near the university library.",
                category="Wallet",
                latitude=50.8514,
                longitude=5.6900,
                radius_meters=500,
                contact_email=DEMO_OWNER_EMAIL,
                contact_phone="+31 6 1111 1111",
                prefer_anonymous=False,
                user_id=alex.id,
            )
        )
    else:
        _assign_report(repository, lost, alex)

    library = repository.get_report(DEMO_FOUND_LIBRARY_ID)
    if library is None:
        repository.add_report(
            Report(
                id=DEMO_FOUND_LIBRARY_ID,
                report_type=ReportType.FOUND,
                description="Black wallet found near the university library.",
                category="Wallet",
                latitude=50.8516,
                longitude=5.6902,
                radius_meters=200,
                contact_email=DEMO_FINDER_EMAIL,
                contact_phone="+31 6 2222 2222",
                prefer_anonymous=True,
                user_id=sam.id,
            )
        )
    else:
        _assign_report(repository, library, sam)

    hotel = repository.get_report(DEMO_FOUND_HOTEL_ID)
    if hotel is None:
        repository.add_report(
            Report(
                id=DEMO_FOUND_HOTEL_ID,
                report_type=ReportType.FOUND,
                description="Dark card holder left at a hotel reception.",
                category="Wallet",
                latitude=50.8499,
                longitude=5.6880,
                radius_meters=300,
                contact_email=DEMO_MIA_EMAIL,
                contact_phone="+31 6 3333 3333",
                prefer_anonymous=False,
                user_id=mia.id,
            )
        )
    else:
        hotel.prefer_anonymous = False
        hotel.contact_email = DEMO_MIA_EMAIL
        hotel.contact_phone = hotel.contact_phone or "+31 6 3333 3333"
        hotel.user_id = mia.id
        repository.add_report(hotel)
