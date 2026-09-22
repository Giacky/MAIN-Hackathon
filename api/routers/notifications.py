"""In-app match alerts for the counterpart owner after ranking."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user, get_repository
from api.serializers import notification_public
from database.repository import SQLiteRepository
from models.schemas import User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _payload(repository: SQLiteRepository, user_id: str) -> dict:
    notifications = repository.list_notifications(user_id)
    return {
        "notifications": [notification_public(item) for item in notifications],
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
        "notification": notification_public(notification),
        "unread_count": repository.count_unread_notifications(user.id),
    }
