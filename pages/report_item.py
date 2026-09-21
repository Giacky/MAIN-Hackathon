"""Lost/found report form: details first, then map pins."""

from datetime import date, datetime, time
from pathlib import Path
from uuid import uuid4
import streamlit as st

import page_defs
from database.repository import SQLiteRepository
from models.schemas import LocationGuess, Report, ReportType, as_utc
from pages.account import current_user
from utils.ui import page_nav
from samples.presets import PRESETS
from services.classifier import ReportClassifier
from utils.config import UPLOAD_DIR, ensure_runtime_directories
from utils.images import save_prepared_image
from utils.map_pin import pins, render_location_map, render_pin_details, replace_pins

REPORT_PINS_KEY = "report_location_pins"


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


@st.cache_resource
def _classifier() -> ReportClassifier:
    return ReportClassifier()


def _report_kind() -> str:
    incoming = str(st.session_state.get("report_type", "lost")).lower()
    return "lost" if incoming == "lost" else "found"


def _apply_preset(preset_id: str) -> None:
    preset = PRESETS[preset_id]
    st.session_state["report_type"] = preset["report_type"]
    st.session_state["form_description"] = preset["description"]
    st.session_state["form_event_date"] = date.today()
    st.session_state["form_event_time"] = time(12, 0)
    st.session_state["sample_image_path"] = str(preset["image"])
    st.session_state["sample_preset_label"] = preset["label"]
    if preset["report_type"] == "found":
        st.session_state["form_holding_note"] = "I left it at the front desk."
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
    if "form_event_date" not in st.session_state:
        st.session_state["form_event_date"] = date.today()
    if "form_event_time" not in st.session_state:
        st.session_state["form_event_time"] = time(12, 0)
    if "form_prefer_anonymous" not in st.session_state:
        st.session_state["form_prefer_anonymous"] = _report_kind() == "found"


def _save_uploads(report_id: str, images: list) -> tuple[str, ...]:
    if not images:
        return ()
    ensure_runtime_directories()
    folder = UPLOAD_DIR / report_id
    folder.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for index, uploaded in enumerate(images):
        destination = save_prepared_image(uploaded.getvalue(), folder / f"{index}.jpg")
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
    destination = save_prepared_image(source, folder / "0.jpg")
    return (str(destination),)


def _render_classification(classification) -> None:
    st.subheader("Suggested labels")
    if classification.is_mock:
        st.caption("Placeholder labels (set `LOST_FOUND_MOCK_ML=1`).")
    st.metric("Category", classification.category)
    st.metric("Urgency", classification.urgency)
    st.metric("Sensitive", "yes" if classification.sensitive_item else "no")
    st.info(classification.recommended_handling)


def _render_debug_presets() -> None:
    st.divider()
    with st.expander("Demo: fill a sample report", expanded=False):
        st.caption("Loads a description, photo, and map pin. Then press Submit.")
        columns = st.columns(2)
        for index, preset_id in enumerate(PRESETS.keys()):
            if columns[index % 2].button(
                PRESETS[preset_id]["label"],
                key=f"preset-{preset_id}",
                width="stretch",
            ):
                _queue_preset(preset_id)
                st.rerun()


def render() -> None:
    user = current_user()
    page_nav()
    if user is None:
        st.title("Report an item")
        st.warning("Log in first so this report stays on your account.")
        if st.button("Go to Account", type="primary"):
            st.switch_page(page_defs.account_page)
        return

    _consume_pending_preset()
    _ensure_form_defaults()
    kind = _report_kind()
    is_found = kind == "found"
    st.title("Report a found item" if is_found else "Report a lost item")
    st.caption(
        f"Reporting as {user.display_name}. Contact uses your account email. "
        "Use Home if you meant the other type of report."
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
    if is_found:
        st.text_area(
            "Where is it now?",
            placeholder="Example: I left it at the hotel reception counter.",
            key="form_holding_note",
        )
        st.checkbox(
            "Stay anonymous",
            help="The owner can still propose a public meetup in the app.",
            key="form_prefer_anonymous",
        )
    else:
        st.checkbox(
            "Hide my contact from the finder",
            help="The finder can still propose a public meetup in the app.",
            key="form_prefer_anonymous",
        )
    st.text_input("Phone (optional)", placeholder="+31 6 1234 5678", key="form_contact_phone")

    sample_label = st.session_state.get("sample_preset_label")
    sample_path = st.session_state.get("sample_image_path")
    if sample_label and sample_path and Path(sample_path).is_file():
        st.caption(f"Sample photo ready: **{sample_label}** (used if you don't upload).")

    st.subheader("Where did this happen?")
    st.caption("Click the map to add pins. Skip this if you are not sure.")
    with st.container(border=True):
        render_location_map(
            map_key="report_page",
            height=280,
            session_key=REPORT_PINS_KEY,
        )
    with st.container(border=True):
        st.markdown("**Pin details**")
        render_pin_details(session_key=REPORT_PINS_KEY)

    submitted = st.button("Submit report", type="primary")
    if submitted:
        description = str(st.session_state.get("form_description", "")).strip()
        if not description:
            st.error("Please add a short description before submitting.")
            _render_debug_presets()
            return

        try:
            classification = _classifier().classify(description)
        except Exception as exc:
            st.error(f"Classification failed: {exc}")
            _render_debug_presets()
            return

        location_pins = pins(REPORT_PINS_KEY)
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
        contact_phone = str(st.session_state.get("form_contact_phone", "")).strip()
        holding_note = str(st.session_state.get("form_holding_note", "")).strip()
        report = Report(
            report_type=ReportType.FOUND if is_found else ReportType.LOST,
            description=description,
            category=classification.category,
            urgency=classification.urgency,
            event_time=as_utc(
                datetime.combine(
                    st.session_state["form_event_date"],
                    st.session_state["form_event_time"],
                )
            ),
            latitude=first.latitude if first else None,
            longitude=first.longitude if first else None,
            radius_meters=first.radius_meters if first else None,
            locations=locations,
            contact_email=user.email,
            contact_phone=contact_phone or None,
            prefer_anonymous=bool(st.session_state.get("form_prefer_anonymous", is_found)),
            user_id=user.id,
            holding_note=holding_note or None if is_found else None,
        )
        uploaded_paths = _save_uploads(report.id, list(images or []))
        report.image_paths = uploaded_paths or _attach_sample_image(report.id)
        _repository().add_report(report)
        if is_found:
            st.session_state["matches_prefer_found"] = True
            st.session_state["matches_selected_found_id"] = report.id
        else:
            st.session_state["matches_prefer_found"] = False
            st.session_state["matches_selected_lost_id"] = report.id
        pin_note = (
            f" with {len(locations)} location pin{'s' if len(locations) != 1 else ''}"
            if locations
            else " without a location"
        )
        st.success(f"Saved report {report.id[:8]}{pin_note}.")
        if report.image_paths:
            st.caption(f"Saved {len(report.image_paths)} photo(s).")
        _render_classification(classification)
        if st.button("See matches", type="primary", width="stretch"):
            st.switch_page(page_defs.matches_page)
        if st.button("View on map", width="stretch"):
            st.switch_page(page_defs.map_page)

    _render_debug_presets()
