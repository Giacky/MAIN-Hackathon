"""Password hashing and lightweight session helpers for hackathon login."""

from __future__ import annotations

import hashlib
import hmac
import os

from models.schemas import User

PBKDF2_ROUNDS = 120_000
SESSION_USER_KEY = "auth_user"


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS
    )
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split(":", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), PBKDF2_ROUNDS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def user_session_payload(user: User) -> dict[str, str]:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
    }


def user_from_session(payload: dict[str, str] | None) -> User | None:
    if not payload:
        return None
    return User(
        id=payload["id"],
        email=payload["email"],
        display_name=payload["display_name"],
        password_hash="",
    )
