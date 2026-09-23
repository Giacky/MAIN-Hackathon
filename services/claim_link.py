"""Manual claim links from the map: ensure a match row without overwriting ML scores."""

from __future__ import annotations

from database.repository import SQLiteRepository
from models.schemas import MatchResult, Report, ReportStatus, ReportType, User


class ClaimError(ValueError):
    """Invalid claim_report_id (wrong type, owner, or status)."""


def _type_value(report: Report) -> str:
    kind = report.report_type
    return kind.value if isinstance(kind, ReportType) else str(kind).lower()


def _status_value(report: Report) -> str:
    status = report.status
    return status.value if isinstance(status, ReportStatus) else str(status).lower()


def resolve_pair(new_report: Report, claimed: Report) -> tuple[Report, Report]:
    """Return (lost, found) for a newly filed report claiming an open counterpart."""
    new_type = _type_value(new_report)
    claimed_type = _type_value(claimed)
    if new_type == claimed_type:
        raise ClaimError("claim must be the opposite report type")
    if new_type == ReportType.LOST.value and claimed_type == ReportType.FOUND.value:
        return new_report, claimed
    if new_type == ReportType.FOUND.value and claimed_type == ReportType.LOST.value:
        return claimed, new_report
    raise ClaimError("claim must be the opposite report type")


def validate_claim_target(
    *,
    claimed: Report | None,
    filer: User,
) -> Report:
    if claimed is None:
        raise ClaimError("claim report not found")
    if claimed.user_id == filer.id:
        raise ClaimError("cannot claim your own report")
    if _status_value(claimed) != ReportStatus.OPEN.value:
        raise ClaimError("claim report is not open")
    return claimed


def ensure_manual_claim(
    repository: SQLiteRepository,
    *,
    new_report: Report,
    claimed: Report,
    filer: User,
) -> dict[str, str]:
    """Link new_report to claimed: create a match row if missing, undismiss if present.

    Does not overwrite existing ML scores. Notifies the counterpart when a fresh
    positive link is stored (same path as match_jobs).
    """
    claimed = validate_claim_target(claimed=claimed, filer=filer)
    lost, found = resolve_pair(new_report, claimed)
    existing = repository.get_match(lost.id, found.id)
    created = False
    if existing is None:
        repository.save_match(
            MatchResult(
                lost_report_id=lost.id,
                found_report_id=found.id,
                # Modest placeholder so the pair appears until the ranker runs.
                overall_score=0.55,
                text_score=0.55,
                geo_score=0.55,
                time_score=0.55,
                image_score=None,
                category_score=0.55,
            )
        )
        created = True
    else:
        repository.undismiss_match(lost.id, found.id)

    counterpart_id = claimed.user_id
    if counterpart_id and counterpart_id != filer.id:
        score = existing.overall_score if existing is not None else 0.55
        if created or (existing is not None and existing.overall_score > 0):
            repository.create_match_notification(
                user_id=counterpart_id,
                lost_report_id=lost.id,
                found_report_id=found.id,
                overall_score=max(score, 0.55),
            )
            try:
                from services.push import send_push_to_user

                send_push_to_user(
                    repository,
                    counterpart_id,
                    title="Possible match",
                    body="Someone claimed an item that may be yours.",
                    url=f"/reports/{claimed.id}",
                )
            except Exception:
                pass

    return {"lost_report_id": lost.id, "found_report_id": found.id}
