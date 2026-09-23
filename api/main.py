"""FastAPI application entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from api.deps import get_repository
from api.routers import auth, coordination, demo, health, matches, notifications, push, reports
from services.demo_seed import ensure_demo_data
from services.match_jobs import enqueue_missing_pairs
from utils.config import ensure_runtime_directories

DEFAULT_SESSION_SECRET = "lost-found-demo-session-secret"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_runtime_directories()
    repository = get_repository()
    ensure_demo_data(repository, prune_extras=False)
    # Rank seeded / missing pairs in the background (inline under mock ML).
    enqueue_missing_pairs(repository)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Lost & Found API", lifespan=lifespan)
    secret = os.getenv("LOST_FOUND_SESSION_SECRET", DEFAULT_SESSION_SECRET)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret,
        same_site="lax",
        https_only=False,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(reports.router)
    app.include_router(matches.router)
    app.include_router(notifications.router)
    app.include_router(push.router)
    app.include_router(coordination.router)
    app.include_router(demo.router)
    return app


app = create_app()
