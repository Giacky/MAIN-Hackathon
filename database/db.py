"""SQLite connection and schema initialization."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from utils.config import DATABASE_PATH, ensure_runtime_directories


@contextmanager
def connection(database_path: Path = DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    """Open a row-aware connection and commit or roll back as appropriate."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database = sqlite3.connect(database_path)
    database.row_factory = sqlite3.Row
    try:
        yield database
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()


def initialize_database(database_path: Path = DATABASE_PATH) -> None:
    """Create the small hackathon schema if it does not already exist."""
    ensure_runtime_directories()
    with connection(database_path) as database:
        database.executescript(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT,
                urgency TEXT,
                created_at TEXT NOT NULL,
                event_time TEXT,
                latitude REAL,
                longitude REAL,
                radius_meters REAL,
                image_paths TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches (
                lost_report_id TEXT NOT NULL,
                found_report_id TEXT NOT NULL,
                overall_score REAL NOT NULL,
                text_score REAL NOT NULL,
                image_score REAL,
                geo_score REAL NOT NULL,
                time_score REAL NOT NULL,
                distance_meters REAL,
                PRIMARY KEY (lost_report_id, found_report_id)
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS drop_offs (
                id TEXT PRIMARY KEY,
                match_id TEXT NOT NULL,
                name TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                instructions TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meetups (
                match_id TEXT PRIMARY KEY,
                id TEXT NOT NULL,
                proposed_by TEXT NOT NULL,
                location_name TEXT NOT NULL,
                meeting_time TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        _ensure_columns(
            database,
            "reports",
            {
                "contact_email": "TEXT",
                "contact_phone": "TEXT",
                "prefer_anonymous": "INTEGER NOT NULL DEFAULT 0",
            },
        )


def _ensure_columns(
    database: sqlite3.Connection, table: str, columns: dict[str, str]
) -> None:
    existing = {row[1] for row in database.execute(f"PRAGMA table_info({table})")}
    for name, definition in columns.items():
        if name not in existing:
            database.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
