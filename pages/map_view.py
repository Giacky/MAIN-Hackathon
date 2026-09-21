"""Browse saved lost (blue) and found (green) reports."""

import streamlit as st

from database.repository import SQLiteRepository
from models.schemas import ReportStatus, ReportType
from utils.map_pin import render_reports_map
from utils.ui import page_nav


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def render() -> None:
    page_nav()
    st.title("Map")
    st.caption("Blue pins are lost items. Green pins are found items.")

    reports = [
        report
        for report in _repository().list_reports()
        if report.status != ReportStatus.RECOVERED
    ]
    if not any(
        report.locations or (report.latitude is not None and report.longitude is not None)
        for report in reports
    ):
        st.info("No reports with locations yet. Pin a place when you file a report.")
        return

    lost_count = sum(1 for report in reports if report.report_type == ReportType.LOST)
    found_count = sum(1 for report in reports if report.report_type == ReportType.FOUND)
    st.caption(f"{lost_count} lost · {found_count} found with a saved location.")
    render_reports_map(reports, height=360)
