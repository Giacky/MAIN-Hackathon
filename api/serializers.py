"""Public JSON serializers — never password_hash or filesystem paths."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models.schemas import (
    ClassificationResult,
    MatchResult,
    Meetup,
    ChatMessage,
    Report,
    ReportStatus,
    User,
)
from services.matching_engine import gate_reason


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _status_value(status: ReportStatus | str) -> str:
    if isinstance(status, ReportStatus):
        return status.value
    return str(status)


def user_public(user: User) -> dict[str, str]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
    }


def classification_public(result: ClassificationResult) -> dict[str, Any]:
    return {
        "category": result.category,
        "urgency": result.urgency,
        "sensitive_item": result.sensitive_item,
        "recommended_handling": result.recommended_handling,
        "category_confidence": result.category_confidence,
        "urgency_confidence": result.urgency_confidence,
        "sensitive_confidence": result.sensitive_confidence,
        "category_ranking": [
            {"label": label, "score": score} for label, score in result.category_ranking
        ],
        "is_mock": result.is_mock,
    }


def report_public(
    report: Report,
    *,
    include_contact: bool,
) -> dict[str, Any]:
    locations = [
        {
            "id": loc.id,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "radius_meters": loc.radius_meters,
        }
        for loc in report.locations
    ]
    image_urls = [
        f"/api/reports/{report.id}/images/{index}"
        for index, _ in enumerate(report.image_paths)
    ]
    payload: dict[str, Any] = {
        "id": report.id,
        "report_type": (
            report.report_type.value
            if hasattr(report.report_type, "value")
            else str(report.report_type)
        ),
        "description": report.description,
        "category": report.category,
        "urgency": report.urgency,
        "created_at": _dt(report.created_at),
        "event_time": _dt(report.event_time),
        "latitude": report.latitude,
        "longitude": report.longitude,
        "radius_meters": report.radius_meters,
        "locations": locations,
        "status": _status_value(report.status),
        "prefer_anonymous": report.prefer_anonymous,
        "holding_note": report.holding_note,
        "image_urls": image_urls,
    }
    if include_contact:
        payload["contact_email"] = report.contact_email
        payload["contact_phone"] = report.contact_phone
    return payload


def _visual_from_match(match: MatchResult) -> dict[str, Any] | None:
    """Expose the optional DINOv2 + LightGlue evidence carried on MatchResult.

    Returns null when there is no photo score at all. When a photo score exists
    but the pair was not shortlisted (CLIP fallback, mock ML, or outside the
    DINOv2 top-N), `shortlisted` is False and the evidence fields are null so
    the client can say "not in the visual shortlist" without treating it as an error.
    """
    if match.image_score is None:
        return None
    return {
        "shortlisted": bool(match.visual_shortlisted),
        "dino_score": match.visual_dino_score,
        "inliers": match.visual_inliers,
        "inlier_ratio": match.visual_inlier_ratio,
    }


def match_public(
    match: MatchResult,
    *,
    lost: Report,
    found: Report,
    viewer_user_id: str | None,
) -> dict[str, Any]:
    lost_own = lost.user_id == viewer_user_id
    found_own = found.user_id == viewer_user_id
    return {
        "overall_score": match.overall_score,
        "text_score": match.text_score,
        "image_score": match.image_score,
        "category_score": match.category_score,
        "geo_score": match.geo_score,
        "time_score": match.time_score,
        "distance_meters": match.distance_meters,
        "image_error": match.image_error,
        "gate_reason": gate_reason(match.text_score, match.category_score),
        "visual": _visual_from_match(match),
        "lost": report_public(
            lost, include_contact=lost_own or not lost.prefer_anonymous
        ),
        "found": report_public(
            found, include_contact=found_own or not found.prefer_anonymous
        ),
    }


def meetup_public(meetup: Meetup | None) -> dict[str, Any] | None:
    if meetup is None:
        return None
    return {
        "id": meetup.id,
        "match_id": meetup.match_id,
        "proposed_by": meetup.proposed_by,
        "location_name": meetup.location_name,
        "meeting_time": _dt(meetup.meeting_time),
        "status": (
            meetup.status.value if hasattr(meetup.status, "value") else str(meetup.status)
        ),
        "created_at": _dt(meetup.created_at),
    }


def message_public(message: ChatMessage, viewer_role: str) -> dict[str, Any]:
    from services.coordination import display_name_for_sender

    return {
        "id": message.id,
        "match_id": message.match_id,
        "sender": message.sender,
        "display_name": display_name_for_sender(message.sender, viewer_role),
        "message": message.message,
        "timestamp": _dt(message.timestamp),
    }
