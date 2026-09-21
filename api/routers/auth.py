"""Session cookie auth routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import (
    clear_session_user,
    get_current_user,
    get_repository,
    set_session_user,
)
from api.serializers import user_public
from database.repository import SQLiteRepository
from models.schemas import User
from services.auth import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterBody(BaseModel):
    display_name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginBody(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.post("/register")
def register(
    body: RegisterBody,
    request: Request,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    display_name = body.display_name.strip()
    email = body.email.strip().lower()
    password = body.password
    if not display_name or not email:
        raise HTTPException(status_code=400, detail="display_name and email are required")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="password must be at least 4 characters")
    if repository.get_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    user = repository.add_user(
        User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
        )
    )
    set_session_user(request, user)
    return {"user": user_public(user)}


@router.post("/login")
def login(
    body: LoginBody,
    request: Request,
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    email = body.email.strip().lower()
    user = repository.get_user_by_email(email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    set_session_user(request, user)
    return {"user": user_public(user)}


@router.post("/logout")
def logout(request: Request) -> dict:
    clear_session_user(request)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return {"user": user_public(user)}
