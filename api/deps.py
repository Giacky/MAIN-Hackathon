"""FastAPI dependencies: repository, session user, classifier, matching engine."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from database.repository import SQLiteRepository
from models.schemas import User
from services.auth import user_from_session
from services.classifier import ReportClassifier
from services.matching_engine import MatchingEngine

SESSION_USER_KEY = "user"

_repository_override: SQLiteRepository | None = None


def set_repository_override(repository: SQLiteRepository | None) -> None:
    """Tests swap in a temp-db repository without rebuilding the app."""
    global _repository_override
    _repository_override = repository


def get_repository() -> SQLiteRepository:
    if _repository_override is not None:
        return _repository_override
    return SQLiteRepository()


@lru_cache(maxsize=1)
def get_classifier() -> ReportClassifier:
    return ReportClassifier()


@lru_cache(maxsize=1)
def get_matching_engine() -> MatchingEngine:
    return MatchingEngine()


def get_optional_user(request: Request) -> User | None:
    payload = request.session.get(SESSION_USER_KEY)
    return user_from_session(payload)


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def set_session_user(request: Request, user: User) -> None:
    request.session[SESSION_USER_KEY] = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
    }


def clear_session_user(request: Request) -> None:
    request.session.pop(SESSION_USER_KEY, None)
