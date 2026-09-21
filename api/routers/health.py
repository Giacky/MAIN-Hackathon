"""Health and ML warmup routes."""

from __future__ import annotations

from fastapi import APIRouter

from api import ml_status

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    return ml_status.snapshot()


@router.post("/health/warmup")
def warmup() -> dict:
    state = ml_status.start_warmup()
    return {"state": state}
