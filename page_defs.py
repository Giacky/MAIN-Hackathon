"""st.Page objects shared so other modules can call st.switch_page."""

import streamlit as st

from pages.recovery import render as render_recovery
from pages.report_item import render as render_report_item

report_page: st.Page | None = None
recovery_page: st.Page | None = None


def init() -> None:
    global report_page, recovery_page
    report_page = st.Page(
        render_report_item, title="Report Item", icon="📝", url_path="report-item"
    )
    recovery_page = st.Page(
        render_recovery, title="Recovery", icon="🤝", url_path="recovery"
    )
