"""Background ranking queue: score a report against open counterparts and cache rows."""

from __future__ import annotations

import logging
import queue
import threading
from typing import TYPE_CHECKING

from models.schemas import MatchResult, Report, ReportType
from services.ml_runtime import use_mock_ml

if TYPE_CHECKING:
    from database.repository import SQLiteRepository
    from services.matching_engine import MatchingEngine

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_pending: set[str] = set()
_jobs: queue.Queue[str] = queue.Queue()
_worker: threading.Thread | None = None


def _type_value(report: Report) -> str:
    report_type = report.report_type
    if isinstance(report_type, ReportType):
        return report_type.value
    return str(report_type).lower()


def is_pending(report_id: str) -> bool:
    with _lock:
        return report_id in _pending


def pending_ids() -> set[str]:
    with _lock:
        return set(_pending)


def _notify_counterpart(
    repository: SQLiteRepository,
    match: MatchResult,
    *,
    filing_user_id: str | None,
    lost: Report,
    found: Report,
) -> None:
    if match.overall_score <= 0:
        return
    if lost.user_id == filing_user_id:
        owner_id = found.user_id
    elif found.user_id == filing_user_id:
        owner_id = lost.user_id
    else:
        return
    if not owner_id or owner_id == filing_user_id:
        return
    repository.create_match_notification(
        user_id=owner_id,
        lost_report_id=match.lost_report_id,
        found_report_id=match.found_report_id,
        overall_score=match.overall_score,
    )
    try:
        from services.push import send_push_to_user

        send_push_to_user(
            repository,
            owner_id,
            title="Possible match",
            body="A new item may match one of yours.",
            url=f"/reports/{found.id if lost.user_id == filing_user_id else lost.id}",
        )
    except Exception:
        logger.exception("Web Push for match notification failed")


def _open_counterparts(anchor: Report, open_reports: list[Report]) -> list[Report]:
    anchor_type = _type_value(anchor)
    opposite = (
        ReportType.FOUND.value
        if anchor_type == ReportType.LOST.value
        else ReportType.LOST.value
    )
    return [
        report
        for report in open_reports
        if _type_value(report) == opposite and report.user_id != anchor.user_id
    ]


def _ensure_worker() -> None:
    global _worker
    with _lock:
        if _worker is not None and _worker.is_alive():
            return
        _worker = threading.Thread(target=_worker_loop, daemon=True, name="match-jobs")
        _worker.start()


def _worker_loop() -> None:
    while True:
        report_id = _jobs.get()
        try:
            _run_job(report_id)
        except Exception:
            logger.exception("Match job failed for %s", report_id)
        finally:
            with _lock:
                _pending.discard(report_id)
            _jobs.task_done()


def _run_job(report_id: str) -> None:
    from api.deps import get_matching_engine, get_repository

    repository = get_repository()
    engine = get_matching_engine()
    rank_and_store(report_id, repository=repository, engine=engine)


def rank_and_store(
    report_id: str,
    *,
    repository: SQLiteRepository,
    engine: MatchingEngine,
) -> None:
    """Rank one report against open opposite-type counterparts and persist pairs."""
    anchor = repository.get_report(report_id)
    if anchor is None:
        return

    open_reports = repository.list_open_reports()
    counterparts = _open_counterparts(anchor, open_reports)
    if not counterparts:
        return

    if _type_value(anchor) == ReportType.LOST.value:
        for match in engine.rank_matches(anchor, counterparts):
            repository.save_match(match)
            found = next(
                (report for report in counterparts if report.id == match.found_report_id),
                None,
            )
            if found is not None:
                _notify_counterpart(
                    repository,
                    match,
                    filing_user_id=anchor.user_id,
                    lost=anchor,
                    found=found,
                )
        return

    if _type_value(anchor) != ReportType.FOUND.value:
        return

    seen: set[tuple[str, str]] = set()
    for lost in counterparts:
        results = engine.rank_matches(lost, [anchor])
        if not results:
            continue
        match = results[0]
        key = (match.lost_report_id, match.found_report_id)
        if key in seen:
            continue
        seen.add(key)
        repository.save_match(match)
        _notify_counterpart(
            repository,
            match,
            filing_user_id=anchor.user_id,
            lost=lost,
            found=anchor,
        )


def enqueue(report_id: str) -> None:
    """Queue ranking for ``report_id``. Non-blocking in real ML; inline under mock."""
    if not report_id:
        return
    with _lock:
        if report_id in _pending:
            return
        _pending.add(report_id)

    if use_mock_ml():
        try:
            _run_job(report_id)
        except Exception:
            logger.exception("Inline match job failed for %s", report_id)
        finally:
            with _lock:
                _pending.discard(report_id)
        return

    _ensure_worker()
    _jobs.put(report_id)


def enqueue_missing_pairs(repository: SQLiteRepository) -> None:
    """Enqueue open reports that still lack a stored pair against open counterparts.

    Prefers lost anchors (one ``rank_matches`` covers all founds). Found reports are
    only enqueued when a counterpart lost was not itself queued in this pass.
    """
    open_reports = repository.list_open_reports()
    existing = {
        (match.lost_report_id, match.found_report_id)
        for match in repository.list_matches()
    }
    lost_reports = [
        report
        for report in open_reports
        if _type_value(report) == ReportType.LOST.value
    ]
    found_reports = [
        report
        for report in open_reports
        if _type_value(report) == ReportType.FOUND.value
    ]

    queued_lost: set[str] = set()
    for lost in lost_reports:
        counterparts = [
            found
            for found in found_reports
            if found.user_id != lost.user_id
        ]
        if any((lost.id, found.id) not in existing for found in counterparts):
            enqueue(lost.id)
            queued_lost.add(lost.id)

    for found in found_reports:
        counterparts = [
            lost
            for lost in lost_reports
            if lost.user_id != found.user_id
        ]
        if any(
            (lost.id, found.id) not in existing and lost.id not in queued_lost
            for lost in counterparts
        ):
            enqueue(found.id)


def is_computing_for(report_id: str, repository: SQLiteRepository) -> bool:
    """True while this report or an open counterpart that may still write a pair is pending."""
    pending = pending_ids()
    if report_id in pending:
        return True
    anchor = repository.get_report(report_id)
    if anchor is None:
        return False
    open_reports = repository.list_open_reports()
    for other in _open_counterparts(anchor, open_reports):
        if other.id in pending:
            return True
    return False
