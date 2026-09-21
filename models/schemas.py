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
