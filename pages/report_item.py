"""Lost/found report form."""

from datetime import datetime

import streamlit as st

from database.repository import SQLiteRepository
from models.schemas import Report, ReportType


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def render() -> None:
    """Render the input shape expected by services and persistence."""
    st.title("Report an item")
    st.caption("This form demonstrates the shared Report contract.")

    initial_type = st.session_state.get("report_type", ReportType.LOST.value)
    initial_index = 0 if initial_type == ReportType.LOST.value else 1

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

        st.markdown("**Approximate location**")
        latitude_column, longitude_column, radius_column = st.columns(3)
        latitude = latitude_column.number_input(
            "Latitude", min_value=-90.0, max_value=90.0, value=50.8514, format="%.6f"
        )
        longitude = longitude_column.number_input(
            "Longitude", min_value=-180.0, max_value=180.0, value=5.6900, format="%.6f"
        )
        radius_meters = radius_column.number_input(
            "Search radius (m)", min_value=10, max_value=100_000, value=500, step=50
        )

        st.markdown("**How can the other person reach you? (optional)**")
        contact_email = st.text_input("Email", placeholder="you@example.com")
        contact_phone = st.text_input("Phone", placeholder="+31 6 1234 5678")
        if report_type_value == "Found":
            prefer_anonymous = st.checkbox(
                "Stay anonymous",
                value=True,
                help="The owner can still arrange a meetup in the app. Your email and phone stay hidden until you turn this off.",
            )
        else:
            prefer_anonymous = st.checkbox(
                "Hide my contact from the finder",
                value=False,
            )
        submitted = st.form_submit_button("Submit report", type="primary")

    if submitted:
        if not description.strip():
            st.error("Please add a short description before submitting.")
            return

        report = Report(
            report_type=ReportType(report_type_value.lower()),
            description=description.strip(),
            event_time=datetime.combine(event_date, event_time),
            latitude=latitude,
            longitude=longitude,
            radius_meters=float(radius_meters),
            # Upload persistence is intentionally left to the integration workstream.
            image_paths=(),
            contact_email=contact_email.strip() or None,
            contact_phone=contact_phone.strip() or None,
            prefer_anonymous=prefer_anonymous,
        )
        _repository().add_report(report)
        st.success(f"Report {report.id[:8]} saved to the local skeleton database.")
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
                    "image_paths": report.image_paths,
                    "status": report.status.value,
                    "contact_email": report.contact_email,
                    "contact_phone": report.contact_phone,
                    "prefer_anonymous": report.prefer_anonymous,
                }
            )
