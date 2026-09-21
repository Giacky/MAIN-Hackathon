"""Shared Streamlit layout helpers for a phone-first UI."""

from __future__ import annotations

from typing import Any

import streamlit as st

_MOBILE_CSS = """
<style>
div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
header[data-testid="stHeader"] {background: transparent;}
/* Clear the sidebar hamburger above the top app nav. */
.block-container {
  padding-top: 2.75rem;
  padding-bottom: 2rem;
  max-width: 52rem;
}
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
  .block-container {padding: 2.6rem 0.7rem 2rem;}
  button[kind] {min-height: 2.55rem;}
}
div[data-testid="stTabs"] button {font-size: 0.95rem;}
</style>
"""


def inject_mobile_css() -> None:
    st.markdown(_MOBILE_CSS, unsafe_allow_html=True)


def page_header(*, back_page: Any | None = None, back_label: str = "Back") -> None:
    """Optional contextual back control only."""
    if back_page is None:
        return
    if st.button(back_label, key="nav-back"):
        st.switch_page(back_page)


def page_footer_nav(*, current: str | None = None) -> None:
    """App nav bar (rendered at the top of each screen)."""
    import page_defs

    destinations: list[tuple[str, str, Any]] = [
        ("home", "Home", page_defs.home_page),
        ("report", "Report", page_defs.report_page),
        ("matches", "Matches", page_defs.matches_page),
        ("map", "Map", page_defs.map_page),
        ("pickup", "Pickup", page_defs.recovery_page),
        ("account", "Account", page_defs.account_page),
    ]

    st.caption("Go to")
    columns = st.columns(len(destinations))
    for column, (slug, label, page) in zip(columns, destinations):
        with column:
            is_current = current == slug
            if st.button(
                label,
                key=f"footer-nav-{slug}",
                width="stretch",
                type="primary" if is_current else "secondary",
                disabled=is_current,
            ):
                st.switch_page(page)
    st.divider()
