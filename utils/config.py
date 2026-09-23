"""Portable, environment-overridable application paths."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_PATH = Path(
    os.getenv("LOST_FOUND_DB_PATH", str(DATA_DIR / "lost_found.sqlite"))
).expanduser()

# Web Push (optional). Generate with: python -m py_vapid --applicationServerKey
# LOST_FOUND_VAPID_PUBLIC_KEY  — URL-safe base64 public key (also served to the browser)
# LOST_FOUND_VAPID_PRIVATE_KEY — URL-safe base64 private key (never commit)
# LOST_FOUND_VAPID_SUBJECT     — contact URI, e.g. mailto:you@example.com
VAPID_PUBLIC_KEY = os.getenv("LOST_FOUND_VAPID_PUBLIC_KEY", "").strip()
VAPID_PRIVATE_KEY = os.getenv("LOST_FOUND_VAPID_PRIVATE_KEY", "").strip()
VAPID_SUBJECT = os.getenv("LOST_FOUND_VAPID_SUBJECT", "mailto:lost-found@localhost").strip()


def vapid_configured() -> bool:
    return bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY)


def ensure_runtime_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
