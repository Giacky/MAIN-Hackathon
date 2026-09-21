"""Shared contracts between UI, matching, and persistence workstreams."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportType(str, Enum):
    LOST = "lost"
    FOUND = "found"


class ReportStatus(str, Enum):
    OPEN = "open"
    RECOVERED = "recovered"


class MeetupStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DECLINED = "declined"


def match_thread_id(lost_report_id: str, found_report_id: str) -> str:
    """Stable coordination id for one lost/found pair."""
    return f"{lost_report_id}:{found_report_id}"


@dataclass(slots=True)
class Report:
    report_type: ReportType
    description: str
    id: str = field(default_factory=lambda: str(uuid4()))
    category: str | None = None
    urgency: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    event_time: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_meters: float | None = None
    image_paths: tuple[str, ...] = ()
    status: ReportStatus = ReportStatus.OPEN
    contact_email: str | None = None
    contact_phone: str | None = None
    prefer_anonymous: bool = False


@dataclass(slots=True)
class ClassificationResult:
    category: str
    urgency: str
    sensitive_item: bool
    recommended_handling: str


@dataclass(slots=True)
class MatchResult:
    lost_report_id: str
    found_report_id: str
    overall_score: float
    text_score: float
    geo_score: float
    time_score: float
    image_score: float | None = None
    distance_meters: float | None = None


@dataclass(slots=True)
class ChatMessage:
    match_id: str
    sender: str
    message: str
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class DropOff:
    match_id: str
    name: str
    latitude: float
    longitude: float
    instructions: str
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Meetup:
    match_id: str
    proposed_by: str
    location_name: str
    meeting_time: datetime
    status: MeetupStatus = MeetupStatus.PROPOSED
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
