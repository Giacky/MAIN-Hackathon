"""Future geographic search view."""

import streamlit as st


def render() -> None:
    st.title("Map")
    st.info("Map integration placeholder")
    st.write(
        "This page will visualize approximate report coordinates, uncertainty radii, "
        "and known drop-off points."
    )
    with st.container(border=True):
        st.subheader("Planned inputs")
        st.code("latitude · longitude · radius_meters", language=None)
