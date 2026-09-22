"""Cached match ranking routes — read stored pair scores, never rank on GET."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.deps import get_current_user, get_repository
from api.serializers import match_public, report_public
from database.repository import SQLiteRepository
from models.schemas import Report, ReportType, User
from services.match_jobs import is_computing_for

router = APIRouter(prefix="/api/matches", tags=["matches"])


class DismissBody(BaseModel):
    lost_report_id: str
    found_report_id: str


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
) -> dict:
    anchor = repository.get_report(report_id)
    if anchor is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if anchor.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not the report owner")

    open_by_id = {
        report.id: report for report in repository.list_open_reports()
    }
    open_by_id[anchor.id] = anchor

    ranked = []
    for match in repository.list_matches_for_report(report_id):
        if _type_value(anchor) == ReportType.LOST.value:
            if match.lost_report_id != anchor.id:
                continue
            counterpart = open_by_id.get(match.found_report_id)
            if counterpart is None:
                continue
            ranked.append(
                match_public(
                    match, lost=anchor, found=counterpart, viewer_user_id=user.id
                )
            )
        elif _type_value(anchor) == ReportType.FOUND.value:
            if match.found_report_id != anchor.id:
                continue
            counterpart = open_by_id.get(match.lost_report_id)
            if counterpart is None:
                continue
            ranked.append(
                match_public(
                    match, lost=counterpart, found=anchor, viewer_user_id=user.id
                )
            )
        else:
            raise HTTPException(status_code=400, detail="Unknown report_type")

    status = (
        "computing"
        if is_computing_for(report_id, repository)
        else "ready"
    )
    return {
        "status": status,
        "anchor": report_public(anchor, include_contact=True),
        "matches": ranked,
    }


@router.patch("/dismiss")
def dismiss_match(
    body: DismissBody,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    lost = repository.get_report(body.lost_report_id)
    found = repository.get_report(body.found_report_id)
    if lost is None or found is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if user.id not in {lost.user_id, found.user_id}:
        raise HTTPException(status_code=403, detail="Not a party to this match")
    if not repository.dismiss_match(body.lost_report_id, body.found_report_id):
        raise HTTPException(status_code=404, detail="Match not found")
    return {"dismissed": True}
