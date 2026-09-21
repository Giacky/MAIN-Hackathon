"""Streamlit entry point and navigation only."""

import streamlit as st

import page_defs
from pages.account import current_user
from pages.map_view import render as render_map
from pages.matches import render as render_matches

st.set_page_config(page_title="Smart Lost & Found", page_icon="🧭", layout="wide")
page_defs.init()


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

    user = current_user()
    if user:
        st.caption(
            f"Signed in as {user.display_name}. Your reports stay attached to this account."
        )
    else:
        st.caption(
            "Create an account so your lost and found items stay with you when you arrange pickup."
        )

    lost_column, found_column = st.columns(2)
    if lost_column.button("I lost something", type="primary", width="stretch"):
        st.session_state["report_type"] = "lost"
        st.switch_page(page_defs.report_page)
    if found_column.button("I found something", width="stretch"):
        st.session_state["report_type"] = "found"
        st.switch_page(page_defs.report_page)

    st.info(
        "Matching runs on this Mac (text, location, time, and CLIP when photos exist). "
        "After a match, Recovery lets both people share contact optionally, "
        "keep the finder anonymous, and agree on a meetup."
    )


home_page = st.Page(
    render_home, title="Home", icon="🏠", url_path="home", default=True
)
matches_page = st.Page(
    render_matches, title="Matches", icon="🧩", url_path="matches"
)
map_page = st.Page(render_map, title="Map", icon="🗺️", url_path="map")

navigation = st.navigation(
    [
        home_page,
        page_defs.report_page,
        matches_page,
        map_page,
        page_defs.recovery_page,
        page_defs.account_page,
    ],
    position="sidebar",
)
if st.session_state.pop("open_recovery", False):
    st.switch_page(
        page_defs.recovery_page,
        query_params={
            "lost": st.session_state.get("recovery_lost_id", ""),
            "found": st.session_state.get("recovery_found_id", ""),
        },
    )
if st.session_state.pop("open_account", False):
    st.switch_page(page_defs.account_page)
navigation.run()
