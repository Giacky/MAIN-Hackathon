"""In-app match alerts for the counterpart owner after ranking."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, get_repository
from api.serializers import notification_public
from database.repository import SQLiteRepository
from models.schemas import Notification, User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _viewer_report_id(
    repository: SQLiteRepository, notification: Notification, user_id: str
) -> str | None:
    """Which of lost/found the current user owns — the report the circle belongs on."""
    lost = repository.get_report(notification.lost_report_id)
    if lost is not None and lost.user_id == user_id:
        return lost.id
    found = repository.get_report(notification.found_report_id)
    if found is not None and found.user_id == user_id:
        return found.id
    return None


def _serialize(
    repository: SQLiteRepository, notification: Notification, user_id: str
) -> dict:
    return notification_public(
        notification,
        report_id=_viewer_report_id(repository, notification, user_id),
    )


def _payload(repository: SQLiteRepository, user_id: str) -> dict:
    notifications = repository.list_notifications(user_id)
    return {
        "notifications": [
            _serialize(repository, item, user_id) for item in notifications
        ],
        "unread_count": repository.count_unread_notifications(user_id),
    }


@router.get("")
def list_notifications(
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    return _payload(repository, user.id)


@router.post("/read-all")
def mark_all_read(
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    repository.mark_all_notifications_read(user.id)
    return _payload(repository, user.id)


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: str,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    notification = repository.mark_notification_read(notification_id, user.id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {
        "notification": _serialize(repository, notification, user.id),
        "unread_count": repository.count_unread_notifications(user.id),
    }
