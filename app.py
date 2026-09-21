"""Streamlit entry point and navigation only."""

import streamlit as st

import page_defs

st.set_page_config(page_title="Smart Lost & Found", page_icon="🧭", layout="wide")
page_defs.init()


@st.cache_resource
def _bootstrap() -> None:
    from services.demo_seed import ensure_demo_data

    ensure_demo_data()


_bootstrap()

st.navigation(page_defs.all_pages(), position="sidebar").run()
