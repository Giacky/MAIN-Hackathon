"""Report summary component."""

import streamlit as st

from models.schemas import Report


def render_item_card(report: Report) -> None:
    """Render a compact report summary from the shared contract."""
    heading = report.category or report.report_type.value.title()
    with st.container(border=True):
        st.subheader(heading)
        st.write(report.description)
        st.caption(f"Status: {report.status.value} · Report {report.id[:8]}")
