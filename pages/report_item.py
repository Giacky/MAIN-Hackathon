"""Lost/found report form: map pins, photos, contact, and classification."""

from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4
import shutil

import streamlit as st

import page_defs
from database.repository import SQLiteRepository
from models.schemas import LocationGuess, Report, ReportType
from pages.account import current_user
from samples.presets import PRESETS
from services.classifier import ReportClassifier
from utils.config import UPLOAD_DIR, ensure_runtime_directories
from utils.map_pin import pins, render_location_map, render_pin_details, replace_pins

REPORT_PINS_KEY = "report_location_pins"


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
        ],
        session_key=REPORT_PINS_KEY,
    )


def _queue_preset(preset_id: str) -> None:
    st.session_state["_pending_preset"] = preset_id


def _consume_pending_preset() -> None:
    preset_id = st.session_state.pop("_pending_preset", None)
    if preset_id:
        _apply_preset(preset_id)


def _ensure_form_defaults() -> None:
    if "form_report_type" not in st.session_state:
        incoming = str(st.session_state.get("report_type", "lost")).lower()
        st.session_state["form_report_type"] = "Lost" if incoming == "lost" else "Found"
    if "form_event_date" not in st.session_state:
        st.session_state["form_event_date"] = date.today()
    if "form_event_time" not in st.session_state:
        st.session_state["form_event_time"] = time(12, 0)
    if "form_prefer_anonymous" not in st.session_state:
        st.session_state["form_prefer_anonymous"] = (
            st.session_state.get("form_report_type") == "Found"
        )


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
    st.subheader("Suggested labels")
    if classification.is_mock:
        st.caption("Placeholder labels (set `LOST_FOUND_MOCK_ML=1`).")
    category_column, urgency_column, sensitive_column = st.columns(3)
    category_column.metric("Category", classification.category)
    urgency_column.metric("Urgency", classification.urgency)
    sensitive_column.metric(
        "Sensitive", "yes" if classification.sensitive_item else "no"
    )
    st.info(classification.recommended_handling)


def _render_debug_presets() -> None:
    st.divider()
    with st.expander("Demo: fill a sample report", expanded=False):
        st.caption("Loads a description, photo, and map pin. Then press Submit.")
        columns = st.columns(3)
        for index, preset_id in enumerate(PRESETS.keys()):
            if columns[index % 3].button(
                PRESETS[preset_id]["label"],
                key=f"preset-{preset_id}",
                width="stretch",
            ):
                _queue_preset(preset_id)
                st.rerun()


def render() -> None:
    st.title("Report an item")
    user = current_user()
    if user is None:
        st.warning("Log in first so this report stays on your account.")
        if st.button("Go to Account", type="primary"):
            st.switch_page(page_defs.account_page)
        return

    st.caption(f"Reporting as {user.display_name}. Pin possible places, then submit.")
    _consume_pending_preset()
    _ensure_form_defaults()
    if "form_contact_email" not in st.session_state:
        st.session_state["form_contact_email"] = user.email

    map_col, detail_col = st.columns([1.7, 1], gap="large")
    with map_col:
        with st.container(border=True):
            st.subheader("Possible locations")
            st.caption("Click the map to add pins. Skip this if you are not sure.")
            render_location_map(
                map_key="report_page",
                height=420,
                session_key=REPORT_PINS_KEY,
            )
    with detail_col:
        with st.container(border=True):
            st.subheader("Pin details")
            render_pin_details(session_key=REPORT_PINS_KEY)

    location_pins = pins(REPORT_PINS_KEY)
    sample_label = st.session_state.get("sample_preset_label")
    sample_path = st.session_state.get("sample_image_path")
    if sample_label and sample_path and Path(sample_path).is_file():
        st.caption(f"Sample photo ready: **{sample_label}** (used if you don't upload).")

    report_kind = str(st.session_state.get("form_report_type", "Lost"))

    with st.form("report-item-form", clear_on_submit=False):
        st.radio(
            "What happened?",
            ["Lost", "Found"],
            horizontal=True,
            key="form_report_type",
        )
        st.text_area(
            "Description",
            placeholder="Example: Small black wallet with a blue card inside...",
            key="form_description",
        )
        images = st.file_uploader(
            "Pictures (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )
        st.date_input("Approximate date", key="form_event_date")
        st.time_input("Approximate time", key="form_event_time")
        st.markdown("**How can the other person reach you? (optional)**")
        st.text_input("Email", placeholder="you@example.com", key="form_contact_email")
        st.text_input("Phone", placeholder="+31 6 1234 5678", key="form_contact_phone")
        anonymous_label = (
            "Stay anonymous"
            if report_kind == "Found"
            else "Hide my contact from the finder"
        )
        st.checkbox(
            anonymous_label,
            help="The other person can still propose a public meetup in the app.",
            key="form_prefer_anonymous",
        )
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
        contact_email = str(st.session_state.get("form_contact_email", "")).strip()
        contact_phone = str(st.session_state.get("form_contact_phone", "")).strip()
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
            contact_email=contact_email or None,
            contact_phone=contact_phone or None,
            prefer_anonymous=bool(st.session_state.get("form_prefer_anonymous", False)),
            user_id=user.id,
        )
        uploaded_paths = _save_uploads(report.id, list(images or []))
        report.image_paths = uploaded_paths or _attach_sample_image(report.id)
        _repository().add_report(report)
        pin_note = (
            f" with {len(locations)} location pin{'s' if len(locations) != 1 else ''}"
            if locations
            else " without a location"
        )
        st.success(f"Saved report {report.id[:8]}{pin_note}.")
        if report.image_paths:
            st.caption(f"Saved {len(report.image_paths)} photo(s).")
        _render_classification(classification)
        match_column, map_column = st.columns(2)
        if match_column.button("See matches", type="primary"):
            st.session_state["demo_lost_id"] = report.id
            st.switch_page(page_defs.matches_page)
        if map_column.button("View on map"):
            st.switch_page(page_defs.map_page)

    _render_debug_presets()
