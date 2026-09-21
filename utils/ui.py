"""Shared Streamlit layout helpers for a phone-first UI."""

import streamlit as st

_MOBILE_CSS = """
<style>
div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 52rem;}
div[data-testid="stSidebar"] {min-width: 13rem;}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
  position: fixed !important;
  top: 0.55rem !important;
  left: 0.45rem !important;
  z-index: 1000000 !important;
}
@media (max-width: 768px) {
  .block-container {padding: 0.6rem 0.7rem 5rem;}
  div[data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.55rem !important;
  }
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }
  button[kind] {min-height: 2.6rem;}
}
div[data-testid="stTabs"] button {font-size: 0.95rem;}
</style>
"""


def inject_mobile_css() -> None:
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


def page_nav(*, back_page=None, back_label: str = "Back") -> None:
    """In-page navigation so a collapsed sidebar is not the only way out."""
    import page_defs

    back_column, home_column, matches_column = st.columns(3)
    if back_page is not None:
        if back_column.button(back_label, width="stretch", key="nav-back"):
            st.switch_page(back_page)
    if home_column.button("Home", width="stretch", key="nav-home"):
        st.switch_page(page_defs.home_page)
    if matches_column.button("Matches", width="stretch", key="nav-matches"):
        st.switch_page(page_defs.matches_page)
