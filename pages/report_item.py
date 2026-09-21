"""Lost/found report form."""

from datetime import datetime

import streamlit as st

from database.repository import SQLiteRepository
from models.schemas import LocationGuess, Report, ReportType
from utils.map_pin import pins, render_location_map, render_pin_details


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def render() -> None:
    """Render the input shape expected by services and persistence."""
    st.title("Report an item")
    st.caption("This form demonstrates the shared Report contract.")

    initial_type = st.session_state.get("report_type", ReportType.LOST.value)
    initial_index = 0 if initial_type == ReportType.LOST.value else 1

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

    with st.form("report-item-form", clear_on_submit=True):
        report_type_value = st.radio(
            "What happened?", ["Lost", "Found"], index=initial_index, horizontal=True
        )
        description = st.text_area(
            "Description",
            placeholder="Example: Small black wallet with a blue card inside...",
        )
        images = st.file_uploader(
            "Pictures (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
        )
        event_date = st.date_input("Approximate date")
        event_time = st.time_input("Approximate time")
        submitted = st.form_submit_button("Submit report", type="primary")

    if submitted:
        if not description.strip():
            st.error("Please add a short description before submitting.")
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
            description=description.strip(),
            event_time=datetime.combine(event_date, event_time),
            latitude=first.latitude if first else None,
            longitude=first.longitude if first else None,
            radius_meters=first.radius_meters if first else None,
            locations=locations,
            image_paths=(),
        )
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
        if images:
            st.info(
                f"{len(images)} image(s) selected. Durable upload storage is a placeholder, "
                "so image bytes were not saved."
            )
        with st.expander("Submitted Report contract"):
            st.json(
                {
                    "id": report.id,
                    "report_type": report.report_type.value,
                    "description": report.description,
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
