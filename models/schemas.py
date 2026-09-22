"""Shared contracts between UI, matching, and persistence workstreams."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Return UTC-aware datetime. Naive values are treated as UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ReportType(str, Enum):
    LOST = "lost"
    FOUND = "found"


class ReportStatus(str, Enum):
    OPEN = "open"
    RECOVERED = "recovered"
    CLOSED = "closed"


class MeetupStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DECLINED = "declined"


def match_thread_id(lost_report_id: str, found_report_id: str) -> str:
    """Stable coordination id for one lost/found pair."""
    return f"{lost_report_id}:{found_report_id}"


@dataclass(slots=True)
class User:
    email: str
    display_name: str
    password_hash: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class LocationGuess:
    """One possible place an item was lost or found, with an uncertainty range."""

    latitude: float
    longitude: float
    radius_meters: float = 200.0
    id: str = field(default_factory=lambda: str(uuid4()))


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
    locations: tuple[LocationGuess, ...] = ()
    image_paths: tuple[str, ...] = ()
    status: ReportStatus = ReportStatus.OPEN
    contact_email: str | None = None
    contact_phone: str | None = None
    prefer_anonymous: bool = False
    user_id: str | None = None
    holding_note: str | None = None


@dataclass(slots=True)
class ClassificationResult:
    category: str
    urgency: str
    sensitive_item: bool
    recommended_handling: str
    category_confidence: float | None = None
    urgency_confidence: float | None = None
    sensitive_confidence: float | None = None
    category_ranking: tuple[tuple[str, float], ...] = ()
    is_mock: bool = False


@dataclass(slots=True)
class MatchResult:
    lost_report_id: str
    found_report_id: str
    overall_score: float
    text_score: float
    geo_score: float
    time_score: float
    image_score: float | None = None
    category_score: float | None = None
    distance_meters: float | None = None
    image_error: str | None = None
    # Optional DINOv2 + LightGlue evidence (persisted with the pair scores).
    visual_shortlisted: bool | None = None
    visual_dino_score: float | None = None
    visual_inliers: int | None = None
    visual_inlier_ratio: float | None = None


@dataclass(slots=True)
class Notification:
    user_id: str
    kind: str
    lost_report_id: str
    found_report_id: str
    overall_score: float
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=utc_now)
    read_at: datetime | None = None


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
