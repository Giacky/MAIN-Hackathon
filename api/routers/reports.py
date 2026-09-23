"""Report CRUD, image URLs, and contact updates."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.deps import get_classifier, get_current_user, get_optional_user, get_repository
from api.serializers import classification_public, report_public
from database.repository import SQLiteRepository
from models.schemas import LocationGuess, Report, ReportStatus, ReportType, User, as_utc
from samples.presets import PRESETS
from services.claim_link import ClaimError, ensure_manual_claim
from services.classifier import ReportClassifier
from services.match_jobs import enqueue
from utils.config import UPLOAD_DIR, ensure_runtime_directories
from utils.images import save_upload_image

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ContactBody(BaseModel):
    contact_email: str | None = None
    contact_phone: str | None = None
    prefer_anonymous: bool = False


class StatusBody(BaseModel):
    status: str


def _parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_locations(raw: str) -> tuple[LocationGuess, ...]:
    try:
        data = json.loads(raw) if raw else []
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="locations must be valid JSON") from exc
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="locations must be a JSON array")
    locations: list[LocationGuess] = []
    for item in data:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="each location must be an object")
        try:
            locations.append(
                LocationGuess(
                    latitude=float(item["latitude"]),
                    longitude=float(item["longitude"]),
                    radius_meters=float(item.get("radius_meters", 200)),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail="location needs latitude, longitude, radius_meters"
            ) from exc
    return tuple(locations)


def _save_uploads(report_id: str, images: list[UploadFile]) -> tuple[str, ...]:
    if not images:
        return ()
    ensure_runtime_directories()
    folder = UPLOAD_DIR / report_id
    folder.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for index, uploaded in enumerate(images):
        data = uploaded.file.read()
        if not data:
            continue
        destination = save_upload_image(data, folder / f"{index}.jpg")
        saved.append(str(destination))
    return tuple(saved)


def _incoming_uploads(images: list[UploadFile] | None) -> list[UploadFile]:
    return [item for item in (images or []) if item.filename]


def _replace_uploads(report_id: str, images: list[UploadFile]) -> tuple[str, ...]:
    """Replace the report's photo set, then save via ``_save_uploads``.

    Sending any new ``images`` files replaces the previous upload set (old
    files in the report folder are removed). Omitting ``images`` keeps the
    existing photos.
    """
    if "/" in report_id or "\\" in report_id or ".." in report_id:
        return _save_uploads(report_id, images)
    folder = (UPLOAD_DIR / report_id).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if folder.is_dir() and str(folder).startswith(str(upload_root)):
        for path in folder.iterdir():
            if path.is_file():
                path.unlink()
    return _save_uploads(report_id, images)


def _status_value(status: ReportStatus | str) -> str:
    if isinstance(status, ReportStatus):
        return status.value
    return str(status)


def _attach_preset_image(report_id: str, preset_id: str) -> tuple[str, ...]:
    preset = PRESETS.get(preset_id)
    if preset is None:
        raise HTTPException(status_code=400, detail="unknown sample_preset_id")
    source = Path(preset["image"])
    if not source.is_file():
        return ()
    ensure_runtime_directories()
    folder = UPLOAD_DIR / report_id
    folder.mkdir(parents=True, exist_ok=True)
    destination = save_upload_image(source, folder / "0.jpg")
    return (str(destination),)


def _viewer_owns(report: Report, user: User | None) -> bool:
    return user is not None and report.user_id == user.id


@router.get("")
def list_reports(
    scope: str = "open",
    user: User | None = Depends(get_optional_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    if scope == "mine":
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        reports = repository.list_reports_for_user(user.id)
        counts = repository.count_positive_matches_for_reports(
            [report.id for report in reports]
        )
        return {
            "reports": [
                report_public(
                    report,
                    include_contact=True,
                    match_count=counts.get(report.id, 0),
                )
                for report in reports
            ]
        }
    if scope != "open":
        raise HTTPException(status_code=400, detail="scope must be mine or open")
    reports = repository.list_open_reports()
    return {
        "reports": [
            report_public(report, include_contact=False) for report in reports
        ]
    }


@router.post("")
async def create_report(
    report_type: str = Form(...),
    description: str = Form(...),
    event_time: str = Form(...),
    prefer_anonymous: str = Form("false"),
    contact_phone: str | None = Form(None),
    holding_note: str | None = Form(None),
    locations: str = Form("[]"),
    sample_preset_id: str | None = Form(None),
    claim_report_id: str | None = Form(None),
    images: list[UploadFile] | None = File(None),
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
    classifier: ReportClassifier = Depends(get_classifier),
) -> dict:
    description = description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="description must not be empty")
    kind = report_type.strip().lower()
    if kind not in {"lost", "found"}:
        raise HTTPException(status_code=400, detail="report_type must be lost or found")
    try:
        when = as_utc(datetime.fromisoformat(event_time.replace("Z", "+00:00")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="event_time must be ISO-8601") from exc

    location_tuple = _parse_locations(locations)
    first = location_tuple[0] if location_tuple else None

    claim_id = (claim_report_id or "").strip() or None
    claimed = None
    if claim_id:
        from services.claim_link import validate_claim_target, resolve_pair

        claimed = repository.get_report(claim_id)
        try:
            claimed = validate_claim_target(claimed=claimed, filer=user)
            # Type check before insert so we don't orphan a report on bad claim.
            probe = Report(
                id="probe",
                report_type=ReportType(kind),
                description=description,
                event_time=when,
                user_id=user.id,
            )
            resolve_pair(probe, claimed)
        except ClaimError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        classification = classifier.classify(description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    report_id = str(uuid4())
    upload_list = [item for item in (images or []) if item.filename]
    image_paths = _save_uploads(report_id, upload_list)
    if not image_paths and sample_preset_id:
        image_paths = _attach_preset_image(report_id, sample_preset_id.strip())

    report = Report(
        id=report_id,
        report_type=ReportType(kind),
        description=description,
        category=classification.category,
        urgency=classification.urgency,
        event_time=when,
        latitude=first.latitude if first else None,
        longitude=first.longitude if first else None,
        radius_meters=first.radius_meters if first else None,
        locations=location_tuple,
        image_paths=image_paths,
        contact_email=user.email,
        contact_phone=(contact_phone or "").strip() or None,
        prefer_anonymous=_parse_bool(prefer_anonymous),
        user_id=user.id,
        holding_note=(holding_note or "").strip() or None,
    )
    repository.add_report(report)

    claim_payload = None
    if claimed is not None:
        try:
            claim_payload = ensure_manual_claim(
                repository, new_report=report, claimed=claimed, filer=user
            )
        except ClaimError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    enqueue(report.id)
    result: dict = {
        "report": report_public(report, include_contact=True),
        "classification": classification_public(classification),
    }
    if claim_payload is not None:
        result["claim"] = claim_payload
    return result


@router.get("/{report_id}")
def get_report(
    report_id: str,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    report = repository.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "report": report_public(
            report, include_contact=_viewer_owns(report, user) or not report.prefer_anonymous
        )
    }


@router.patch("/{report_id}")
async def update_report(
    report_id: str,
    report_type: str = Form(...),
    description: str = Form(...),
    event_time: str = Form(...),
    prefer_anonymous: str = Form("false"),
    contact_phone: str | None = Form(None),
    holding_note: str | None = Form(None),
    locations: str = Form("[]"),
    images: list[UploadFile] | None = File(None),
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
    classifier: ReportClassifier = Depends(get_classifier),
) -> dict:
    """Update an open report owned by the caller.

    Multipart fields match create. New ``images`` replace the previous upload
    set; omitting files keeps existing photos. Description changes reclassify
    and ``enqueue`` rematches (dismissed pairs stay dismissed).
    """
    report = repository.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not the report owner")
    if _status_value(report.status) in {
        ReportStatus.CLOSED.value,
        ReportStatus.RECOVERED.value,
    }:
        raise HTTPException(
            status_code=400, detail="closed or recovered reports cannot be edited"
        )

    description = description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="description must not be empty")
    kind = report_type.strip().lower()
    if kind not in {"lost", "found"}:
        raise HTTPException(status_code=400, detail="report_type must be lost or found")
    try:
        when = as_utc(datetime.fromisoformat(event_time.replace("Z", "+00:00")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="event_time must be ISO-8601") from exc

    location_tuple = _parse_locations(locations)
    first = location_tuple[0] if location_tuple else None

    classification = None
    if description != report.description:
        try:
            classification = classifier.classify(description)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        report.category = classification.category
        report.urgency = classification.urgency

    report.report_type = ReportType(kind)
    report.description = description
    report.event_time = when
    report.latitude = first.latitude if first else None
    report.longitude = first.longitude if first else None
    report.radius_meters = first.radius_meters if first else None
    report.locations = location_tuple
    report.contact_phone = (contact_phone or "").strip() or None
    report.prefer_anonymous = _parse_bool(prefer_anonymous)
    report.holding_note = (holding_note or "").strip() or None

    upload_list = _incoming_uploads(images)
    if upload_list:
        report.image_paths = _replace_uploads(report.id, upload_list)

    repository.add_report(report)
    enqueue(report.id)
    payload: dict = {"report": report_public(report, include_contact=True)}
    if classification is not None:
        payload["classification"] = classification_public(classification)
    return payload


@router.get("/{report_id}/images/{index}")
def get_report_image(report_id: str, index: int) -> FileResponse:
    if index < 0 or "/" in report_id or "\\" in report_id or ".." in report_id:
        raise HTTPException(status_code=404, detail="Image not found")
    base = (UPLOAD_DIR / report_id).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if not str(base).startswith(str(upload_root)):
        raise HTTPException(status_code=404, detail="Image not found")
    path = (base / f"{index}.jpg").resolve()
    if not str(path).startswith(str(base)) or not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/jpeg")


@router.patch("/{report_id}/contact")
def update_contact(
    report_id: str,
    body: ContactBody,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    report = repository.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not the report owner")
    report.contact_email = (body.contact_email or "").strip() or None
    report.contact_phone = (body.contact_phone or "").strip() or None
    report.prefer_anonymous = body.prefer_anonymous
    repository.add_report(report)
    return {"report": report_public(report, include_contact=True)}


@router.patch("/{report_id}/status")
def update_status(
    report_id: str,
    body: StatusBody,
    user: User = Depends(get_current_user),
    repository: SQLiteRepository = Depends(get_repository),
) -> dict:
    report = repository.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not the report owner")
    wanted = body.status.strip().lower()
    if wanted != ReportStatus.CLOSED.value:
        raise HTTPException(status_code=400, detail="status must be closed")
    repository.update_report_status(report_id, ReportStatus.CLOSED)
    closed = repository.get_report(report_id)
    assert closed is not None
    return {"report": report_public(closed, include_contact=True)}
