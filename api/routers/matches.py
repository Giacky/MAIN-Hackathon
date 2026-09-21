"""Live match ranking routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user, get_matching_engine, get_repository
from api.serializers import match_public, report_public
from database.repository import SQLiteRepository
from models.schemas import Report, ReportType, User
from services.matching_engine import MatchingEngine

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _type_value(report: Report) -> str:
    report_type = report.report_type
    if isinstance(report_type, ReportType):
        return report_type.value
    return str(report_type).lower()


@router.get("")
def list_matches(
    report_id: str = Query(...),
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
    engine: MatchingEngine = Depends(get_matching_engine),
) -> dict:
    anchor = repository.get_report(report_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if anchor.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not the report owner")

    open_reports = repository.list_open_reports()
    lost_reports = [
        report
        for report in open_reports
        if _type_value(report) == ReportType.LOST.value and report.user_id != user.id
    ]
    found_reports = [
        report
        for report in open_reports
        if _type_value(report) == ReportType.FOUND.value and report.user_id != user.id
    ]

    by_id = {report.id: report for report in open_reports}
    by_id[anchor.id] = anchor
    ranked = []

    if _type_value(anchor) == ReportType.LOST.value:
        results = engine.rank_matches(anchor, found_reports)
        for match in results:
            repository.save_match(match)
            found = by_id.get(match.found_report_id)
            if found is None:
                continue
            ranked.append(
                match_public(match, lost=anchor, found=found, viewer_user_id=user.id)
            )
    elif _type_value(anchor) == ReportType.FOUND.value:
        pairs = []
        for lost in lost_reports:
            results = engine.rank_matches(lost, [anchor])
            if not results:
                continue
            match = results[0]
            repository.save_match(match)
            pairs.append(match)
        pairs.sort(key=lambda item: item.overall_score, reverse=True)
        for match in pairs:
            lost = by_id.get(match.lost_report_id)
            if lost is None:
                continue
            ranked.append(
                match_public(match, lost=lost, found=anchor, viewer_user_id=user.id)
            )
    else:
        raise HTTPException(status_code=400, detail="Unknown report_type")

    return {
        "anchor": report_public(anchor, include_contact=True),
        "matches": ranked,
    }
