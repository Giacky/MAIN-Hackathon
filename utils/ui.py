"""Shared Streamlit layout helpers for a phone-first UI."""

import streamlit as st

_MOBILE_CSS = """
<style>
div[data-testid="stToolbar"] {visibility: hidden; height: 0;}
header[data-testid="stHeader"] {background: transparent;}
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 52rem;}
div[data-testid="stSidebar"] {min-width: 13rem;}
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
