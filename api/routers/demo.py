"""Demo presets and gated database reset."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import FileResponse

from api.serializers import report_public
from samples.presets import PRESETS, SAMPLES_DIR
from services.demo_seed import seed_demo_reports

router = APIRouter(prefix="/api/demo", tags=["demo"])


def _demo_reset_allowed() -> bool:
    return os.getenv("LOST_FOUND_ALLOW_DEMO_RESET", "").strip() == "1"


@router.get("/presets")
def list_presets() -> dict:
    presets = []
    for preset_id, preset in PRESETS.items():
        presets.append(
            {
                "id": preset_id,
                "label": preset["label"],
                "report_type": preset["report_type"],
                "description": preset["description"],
                "latitude": preset["latitude"],
                "longitude": preset["longitude"],
                "radius_meters": preset["radius_meters"],
                "image_url": f"/api/demo/presets/{preset_id}/image",
            }
        )
    return {"presets": presets}


@router.get("/presets/{preset_id}/image")
def preset_image(preset_id: str) -> FileResponse:
    preset = PRESETS.get(preset_id)
    if preset is None:
        raise HTTPException(status_code=404, detail="Preset not found")
    path = Path(preset["image"]).resolve()
    samples_root = SAMPLES_DIR.resolve()
    if not str(path).startswith(str(samples_root)) or not path.is_file():
        raise HTTPException(status_code=404, detail="Preset image not found")
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(path, media_type=media)


@router.post("/reset")
def reset_demo(
    x_demo_reset: str | None = Header(default=None, alias="X-Demo-Reset"),
) -> dict:
    if not _demo_reset_allowed():
        raise HTTPException(status_code=403, detail="Demo reset is disabled")
    if x_demo_reset != "demo":
        raise HTTPException(status_code=403, detail="Missing or invalid X-Demo-Reset header")
    lost_reports, found_reports = seed_demo_reports()
    return {
        "lost": [report_public(report, include_contact=False) for report in lost_reports],
        "found": [report_public(report, include_contact=False) for report in found_reports],
    }
