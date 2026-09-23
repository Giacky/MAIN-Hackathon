"""Web Push subscription endpoints (VAPID)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_current_user, get_repository
from database.repository import SQLiteRepository
from models.schemas import User
from services.push import public_vapid_key
from utils.config import vapid_configured

router = APIRouter(prefix="/api/push", tags=["push"])


class PushSubscribeBody(BaseModel):
    endpoint: str = Field(min_length=1)
    keys: dict[str, str]


class PushUnsubscribeBody(BaseModel):
    endpoint: str = Field(min_length=1)


@router.get("/vapid-public-key")
def get_vapid_public_key() -> dict:
    key = public_vapid_key()
    return {"public_key": key, "configured": vapid_configured() and bool(key)}


@router.post("/subscribe")
def subscribe(
    body: PushSubscribeBody,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    if not vapid_configured():
        raise HTTPException(status_code=503, detail="Web Push is not configured")
    p256dh = (body.keys.get("p256dh") or "").strip()
    auth = (body.keys.get("auth") or "").strip()
    if not p256dh or not auth:
        raise HTTPException(status_code=400, detail="keys.p256dh and keys.auth required")
    repository.save_push_subscription(
        user_id=user.id,
        endpoint=body.endpoint.strip(),
        p256dh=p256dh,
        auth=auth,
    )
    return {"subscribed": True}


@router.post("/unsubscribe")
def unsubscribe(
    body: PushUnsubscribeBody,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    removed = repository.delete_push_subscription(
        user_id=user.id, endpoint=body.endpoint.strip()
    )
    return {"unsubscribed": removed}
