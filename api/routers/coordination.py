"""Pickup coordination: contact, notes, meetup, recovered."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_current_user, get_repository
from api.serializers import meetup_public, message_public, report_public
from database.repository import SQLiteRepository
from models.schemas import (
    ChatMessage,
    Meetup,
    MeetupStatus,
    ReportStatus,
    User,
    as_utc,
    match_thread_id,
)
from services.coordination import (
    can_respond_to_meetup,
    contact_for_viewer,
    role_for_user,
)

router = APIRouter(prefix="/api/coordination", tags=["coordination"])


class MessageBody(BaseModel):
    message: str = Field(min_length=1)


class MeetupBody(BaseModel):
    location_name: str = Field(min_length=1)
    meeting_time: str = Field(min_length=1)


def _load_pair(
    lost_id: str,
    found_id: str,
    user: User,
    repository: SQLiteRepository,
):
    lost = repository.get_report(lost_id)
    found = repository.get_report(found_id)
    if lost is None or found is None:
        raise HTTPException(status_code=404, detail="Report not found")
    role = role_for_user(user.id, lost, found, email=user.email)
    if role not in {"lost", "found"}:
        raise HTTPException(status_code=403, detail="Not a party to this match")
    return lost, found, role


@router.get("/{lost_id}/{found_id}")
def get_coordination(
    lost_id: str,
    found_id: str,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    lost, found, role = _load_pair(lost_id, found_id, user, repository)
    match_id = match_thread_id(lost.id, found.id)
    other = found if role == "lost" else lost
    email, phone = contact_for_viewer(other, role)
    other_contact = None
    if email or phone:
        other_contact = {"email": email, "phone": phone}
    messages = [
        message_public(message, role)
        for message in repository.list_chat_messages(match_id)
    ]
    recovered = (
        str(lost.status.value if hasattr(lost.status, "value") else lost.status)
        == ReportStatus.RECOVERED.value
        or str(found.status.value if hasattr(found.status, "value") else found.status)
        == ReportStatus.RECOVERED.value
    )
    return {
        "role": role,
        "lost": report_public(lost, include_contact=role == "lost"),
        "found": report_public(found, include_contact=role == "found"),
        "other_contact": other_contact,
        "meetup": meetup_public(repository.get_meetup(match_id)),
        "messages": messages,
        "recovered": recovered,
    }


@router.post("/{lost_id}/{found_id}/messages")
def post_message(
    lost_id: str,
    found_id: str,
    body: MessageBody,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    lost, found, role = _load_pair(lost_id, found_id, user, repository)
    text = body.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="message must not be empty")
    match_id = match_thread_id(lost.id, found.id)
    message = repository.add_chat_message(
        ChatMessage(match_id=match_id, sender=role, message=text)
    )
    return {"message": message_public(message, role)}


@router.post("/{lost_id}/{found_id}/meetup")
def propose_meetup(
    lost_id: str,
    found_id: str,
    body: MeetupBody,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    lost, found, role = _load_pair(lost_id, found_id, user, repository)
    location_name = body.location_name.strip()
    if not location_name:
        raise HTTPException(status_code=400, detail="location_name is required")
    try:
        meeting_time = as_utc(
            datetime.fromisoformat(body.meeting_time.replace("Z", "+00:00"))
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="meeting_time must be ISO-8601") from exc
    if meeting_time is None:
        raise HTTPException(status_code=400, detail="meeting_time is required")
    match_id = match_thread_id(lost.id, found.id)
    meetup = repository.save_meetup(
        Meetup(
            match_id=match_id,
            proposed_by=role,
            location_name=location_name,
            meeting_time=meeting_time,
            status=MeetupStatus.PROPOSED,
        )
    )
    return {"meetup": meetup_public(meetup)}


@router.post("/{lost_id}/{found_id}/meetup/accept")
def accept_meetup(
    lost_id: str,
    found_id: str,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    lost, found, role = _load_pair(lost_id, found_id, user, repository)
    match_id = match_thread_id(lost.id, found.id)
    meetup = repository.get_meetup(match_id)
    if meetup is None:
        raise HTTPException(status_code=404, detail="No meetup proposed")
    if not can_respond_to_meetup(meetup, role):
        raise HTTPException(status_code=403, detail="Cannot accept this meetup")
    repository.update_meetup_status(match_id, MeetupStatus.ACCEPTED)
    return {"meetup": meetup_public(repository.get_meetup(match_id))}


@router.post("/{lost_id}/{found_id}/meetup/decline")
def decline_meetup(
    lost_id: str,
    found_id: str,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    lost, found, role = _load_pair(lost_id, found_id, user, repository)
    match_id = match_thread_id(lost.id, found.id)
    meetup = repository.get_meetup(match_id)
    if meetup is None:
        raise HTTPException(status_code=404, detail="No meetup proposed")
    if not can_respond_to_meetup(meetup, role):
        raise HTTPException(status_code=403, detail="Cannot decline this meetup")
    repository.update_meetup_status(match_id, MeetupStatus.DECLINED)
    return {"meetup": meetup_public(repository.get_meetup(match_id))}


@router.post("/{lost_id}/{found_id}/recovered")
def mark_recovered(
    lost_id: str,
    found_id: str,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    lost, found, _role = _load_pair(lost_id, found_id, user, repository)
    repository.mark_recovered(lost.id)
    repository.mark_recovered(found.id)
    lost = repository.get_report(lost.id)
    found = repository.get_report(found.id)
    return {
        "lost": report_public(lost, include_contact=False),
        "found": report_public(found, include_contact=False),
        "recovered": True,
    }
