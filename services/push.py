"""Optional Web Push delivery (VAPID). No-ops when keys are unset."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from utils.config import VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY, VAPID_SUBJECT, vapid_configured

if TYPE_CHECKING:
    from database.repository import SQLiteRepository

logger = logging.getLogger(__name__)


def send_push_to_user(
    repository: SQLiteRepository,
    user_id: str,
    *,
    title: str,
    body: str,
    url: str = "/",
) -> None:
    if not vapid_configured() or not user_id:
        return
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning("pywebpush not installed; skipping Web Push")
        return

    payload = json.dumps({"title": title, "body": body, "url": url})
    vapid_claims = {"sub": VAPID_SUBJECT}
    for sub in repository.list_push_subscriptions(user_id):
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {404, 410}:
                repository.delete_push_endpoint(sub["endpoint"])
            else:
                logger.warning("Web Push failed for %s: %s", user_id, exc)
        except Exception:
            logger.exception("Web Push failed for %s", user_id)


def public_vapid_key() -> str | None:
    return VAPID_PUBLIC_KEY or None
