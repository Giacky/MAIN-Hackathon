"""Streamlit entry point and navigation only."""

import streamlit as st

from pages.map_view import render as render_map
from pages.matches import render as render_matches
from pages.recovery import render as render_recovery
from pages.report_item import render as render_report_item


st.set_page_config(page_title="Smart Lost & Found", page_icon="🧭", layout="wide")


@st.cache_resource
def _prepare_ml() -> str:
    from services.ml_runtime import use_mock_ml, warmup_text_models

    if use_mock_ml():
        return "mock"
    try:
        warmup_text_models()
    except Exception:
        return "unavailable"
    return "ready"


_prepare_ml()


def render_home() -> None:
    """Render the landing page."""
    st.title("🧭 Smart Lost & Found")
    st.subheader("Helping lost items find their way home.")
    st.write(
        "Report a lost or found item, then let matching services rank likely pairs "
        "using descriptions, place, time, and eventually images."
    )

    lost_column, found_column = st.columns(2)
    if lost_column.button("I lost something", type="primary", width="stretch"):
        st.session_state["report_type"] = "lost"
        st.switch_page(report_page)
    if found_column.button("I found something", width="stretch"):
        st.session_state["report_type"] = "found"
        st.switch_page(report_page)

    st.info(
        "Matching runs on this Mac (text, location, time, and CLIP when photos exist). "
        "Chat and map are still placeholders."
    )


home_page = st.Page(
    render_home, title="Home", icon="🏠", url_path="home", default=True
)
report_page = st.Page(
    render_report_item, title="Report Item", icon="📝", url_path="report-item"
)
matches_page = st.Page(
    render_matches, title="Matches", icon="🧩", url_path="matches"
)
map_page = st.Page(render_map, title="Map", icon="🗺️", url_path="map")
recovery_page = st.Page(
    render_recovery, title="Recovery", icon="🤝", url_path="recovery"
)

navigation = st.navigation(
    [home_page, report_page, matches_page, map_page, recovery_page],
    position="sidebar",
)
navigation.run()
