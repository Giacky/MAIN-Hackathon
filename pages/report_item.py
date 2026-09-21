"""Lost/found report form with one-click sample fill for demo testing."""

from datetime import date, datetime, time
from pathlib import Path
import shutil

import streamlit as st

from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from samples.presets import PRESETS
from services.classifier import ReportClassifier
from utils.config import UPLOAD_DIR, ensure_runtime_directories


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
    st.session_state["form_latitude"] = float(preset["latitude"])
    st.session_state["form_longitude"] = float(preset["longitude"])
    st.session_state["form_radius_meters"] = int(preset["radius_meters"])
    st.session_state["form_event_date"] = date.today()
    st.session_state["form_event_time"] = time(12, 0)
    st.session_state["sample_image_path"] = str(preset["image"])
    st.session_state["sample_preset_label"] = preset["label"]


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

        st.markdown("**Approximate location**")
        latitude_column, longitude_column, radius_column = st.columns(3)
        latitude_column.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            format="%.6f",
            key="form_latitude",
        )
        longitude_column.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            format="%.6f",
            key="form_longitude",
        )
        radius_column.number_input(
            "Search radius (m)",
            min_value=10,
            max_value=100_000,
            step=50,
            key="form_radius_meters",
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

        report = Report(
            report_type=ReportType(report_type_value.lower()),
            description=description,
            category=classification.category,
            urgency=classification.urgency,
            event_time=datetime.combine(
                st.session_state["form_event_date"],
                st.session_state["form_event_time"],
            ),
            latitude=float(st.session_state["form_latitude"]),
            longitude=float(st.session_state["form_longitude"]),
            radius_meters=float(st.session_state["form_radius_meters"]),
        )
        uploaded_paths = _save_uploads(report.id, list(images or []))
        report.image_paths = uploaded_paths or _attach_sample_image(report.id)
        _repository().add_report(report)
        st.success(f"Report {report.id[:8]} saved to the local skeleton database.")
        _render_classification(classification)

        if report.image_paths:
            st.caption(f"Saved {len(report.image_paths)} image(s) on this Mac.")
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
                    "image_paths": report.image_paths,
                    "status": report.status.value,
                }
            )

    _render_debug_presets()
