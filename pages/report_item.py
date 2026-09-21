"""Lost/found report form with map pins and one-click sample fill."""

from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4
import shutil

import streamlit as st

from database.repository import SQLiteRepository
from models.schemas import LocationGuess, Report, ReportType
from samples.presets import PRESETS
from services.classifier import ReportClassifier
from utils.config import UPLOAD_DIR, ensure_runtime_directories
from utils.map_pin import pins, render_location_map, render_pin_details, replace_pins


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


@st.cache_resource
def _classifier() -> ReportClassifier:
    return ReportClassifier()


def _apply_preset(preset_id: str) -> None:
    preset = PRESETS[preset_id]
    st.session_state["report_type"] = preset["report_type"]
    st.session_state["form_report_type"] = (
        "Lost" if preset["report_type"] == "lost" else "Found"
    )
    st.session_state["form_description"] = preset["description"]
    st.session_state["form_event_date"] = date.today()
    st.session_state["form_event_time"] = time(12, 0)
    st.session_state["sample_image_path"] = str(preset["image"])
    st.session_state["sample_preset_label"] = preset["label"]
    replace_pins(
        [
            {
                "id": str(uuid4()),
                "lat": float(preset["latitude"]),
                "lon": float(preset["longitude"]),
                "radius_meters": float(preset["radius_meters"]),
                "label": preset["label"],
            }
        ]
    )


def _ensure_form_defaults() -> None:
    if "form_description" not in st.session_state:
        _apply_preset("lost_wallet")


def _save_uploads(report_id: str, images: list) -> tuple[str, ...]:
    if not images:
        return ()
    ensure_runtime_directories()
    folder = UPLOAD_DIR / report_id
    folder.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for index, uploaded in enumerate(images):
        suffix = Path(uploaded.name).suffix.lower() or ".jpg"
        destination = folder / f"{index}{suffix}"
        destination.write_bytes(uploaded.getvalue())
        saved.append(str(destination))
    return tuple(saved)


def _attach_sample_image(report_id: str) -> tuple[str, ...]:
    sample = st.session_state.get("sample_image_path")
    if not sample:
        return ()
    source = Path(sample)
    if not source.is_file():
        return ()
    ensure_runtime_directories()
    folder = UPLOAD_DIR / report_id
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"0{source.suffix.lower() or '.png'}"
    shutil.copy2(source, destination)
    return (str(destination),)


def _render_classification(classification) -> None:
    st.subheader("DeBERTa model output")
    if classification.is_mock:
        st.warning(
            "Mock classification (unset `LOST_FOUND_MOCK_ML` and ensure the model "
            "is downloaded for real DeBERTa scores)."
        )
    else:
        st.caption(
            "Zero-shot labels from `MoritzLaurer/deberta-v3-base-zeroshot-v2.0` "
            "on the description text."
        )

    category_column, urgency_column, sensitive_column = st.columns(3)
    category_column.metric(
        "Category",
        classification.category,
        (
            f"{classification.category_confidence:.0%} confidence"
            if classification.category_confidence is not None
            else None
        ),
    )
    urgency_column.metric(
        "Urgency",
        classification.urgency,
        (
            f"{classification.urgency_confidence:.0%} confidence"
            if classification.urgency_confidence is not None
            else None
        ),
    )
    sensitive_column.metric(
        "Sensitive",
        "yes" if classification.sensitive_item else "no",
        (
            f"{classification.sensitive_confidence:.0%} confidence"
            if classification.sensitive_confidence is not None
            else None
        ),
    )
    st.info(classification.recommended_handling)

    if classification.category_ranking:
        with st.expander("All category scores (ranked)"):
            st.dataframe(
                [
                    {"label": label, "score": round(score, 4)}
                    for label, score in classification.category_ranking
                ],
                hide_index=True,
                width="stretch",
            )


def _render_debug_presets() -> None:
    st.divider()
    with st.expander("Demo / debug tools", expanded=False):
        st.caption("Quick-fill sample reports, then use Submit above.")
        columns = st.columns(3)
        for index, preset_id in enumerate(PRESETS.keys()):
            if columns[index % 3].button(
                PRESETS[preset_id]["label"],
                key=f"preset-{preset_id}",
                width="stretch",
            ):
                _apply_preset(preset_id)
                st.rerun()


def render() -> None:
    """Render the input shape expected by services and persistence."""
    st.title("Report an item")
    st.caption("Fill the form and submit. Demo presets are at the bottom.")

    _ensure_form_defaults()

    map_col, detail_col = st.columns([1.7, 1], gap="large")
    with map_col:
        with st.container(border=True):
            st.subheader("Possible locations", icon=":material/map:")
            st.caption(
                "Click to add pins, or skip the map if you are not sure. "
                "Each pin can have its own range."
            )
            render_location_map(map_key="report_page", height=420)
    with detail_col:
        with st.container(border=True):
            st.subheader("Pin details", icon=":material/place:")
            render_pin_details()

    location_pins = pins()
    sample_label = st.session_state.get("sample_preset_label", "sample")
    sample_path = st.session_state.get("sample_image_path")
    if sample_path and Path(sample_path).is_file():
        st.caption(f"Sample photo ready: **{sample_label}** (used if you don't upload).")

    with st.form("report-item-form", clear_on_submit=False):
        st.radio(
            "What happened?",
            ["Lost", "Found"],
            horizontal=True,
            key="form_report_type",
        )
        st.text_area("Description", key="form_description")
        images = st.file_uploader(
            "Pictures (optional — sample photo is used if empty)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )
        st.date_input("Approximate date", key="form_event_date")
        st.time_input("Approximate time", key="form_event_time")
        submitted = st.form_submit_button("Submit report", type="primary")

    if submitted:
        description = str(st.session_state.get("form_description", "")).strip()
        if not description:
            st.error("Please add a short description before submitting.")
            _render_debug_presets()
            return

        report_type_value = str(st.session_state.get("form_report_type", "Lost"))
        try:
            classification = _classifier().classify(description)
        except Exception as exc:
            st.error(f"Classification failed: {exc}")
            _render_debug_presets()
            return

        locations = tuple(
            LocationGuess(
                id=pin["id"],
                latitude=pin["lat"],
                longitude=pin["lon"],
                radius_meters=float(pin["radius_meters"]),
            )
            for pin in location_pins
        )
        first = locations[0] if locations else None
        report = Report(
            report_type=ReportType(report_type_value.lower()),
            description=description,
            category=classification.category,
            urgency=classification.urgency,
            event_time=datetime.combine(
                st.session_state["form_event_date"],
                st.session_state["form_event_time"],
            ),
            latitude=first.latitude if first else None,
            longitude=first.longitude if first else None,
            radius_meters=first.radius_meters if first else None,
            locations=locations,
        )
        uploaded_paths = _save_uploads(report.id, list(images or []))
        report.image_paths = uploaded_paths or _attach_sample_image(report.id)
        _repository().add_report(report)
        if locations:
            st.success(
                f"Report {report.id[:8]} saved with {len(locations)} location guess"
                f"{'es' if len(locations) != 1 else ''}."
            )
        else:
            st.success(
                f"Report {report.id[:8]} saved without a location. You can add pins later."
            )
        if report.image_paths:
            st.caption(f"Saved {len(report.image_paths)} image(s) on this Mac.")
        _render_classification(classification)
        with st.expander("Submitted Report contract"):
            st.json(
                {
                    "id": report.id,
                    "report_type": report.report_type.value,
                    "description": report.description,
                    "category": report.category,
                    "urgency": report.urgency,
                    "classification": {
                        "category": classification.category,
                        "category_confidence": classification.category_confidence,
                        "urgency": classification.urgency,
                        "urgency_confidence": classification.urgency_confidence,
                        "sensitive_item": classification.sensitive_item,
                        "sensitive_confidence": classification.sensitive_confidence,
                        "recommended_handling": classification.recommended_handling,
                        "is_mock": classification.is_mock,
                    },
                    "event_time": report.event_time.isoformat(),
                    "latitude": report.latitude,
                    "longitude": report.longitude,
                    "radius_meters": report.radius_meters,
                    "locations": [
                        {
                            "id": location.id,
                            "latitude": location.latitude,
                            "longitude": location.longitude,
                            "radius_meters": location.radius_meters,
                        }
                        for location in report.locations
                    ],
                    "image_paths": report.image_paths,
                    "status": report.status.value,
                }
            )

    _render_debug_presets()
