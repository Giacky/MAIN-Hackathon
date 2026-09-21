"""Potential-match component."""

import streamlit as st

from models.schemas import MatchResult, Report


def _percent(score: float) -> str:
    return f"{score:.0%}"


def render_match_card(match: MatchResult, found_report: Report | None = None) -> None:
    """Render one match and its inspectable component scores."""
    with st.container(border=True):
        st.subheader(f"Potential Match — {_percent(match.overall_score)}")
        if found_report:
            st.write(found_report.description)

        text_column, geo_column, time_column, image_column = st.columns(4)
        text_column.metric("Text", _percent(match.text_score))
        geo_column.metric("Location", _percent(match.geo_score))
        time_column.metric("Time", _percent(match.time_score))
        image_column.metric(
            "Image", _percent(match.image_score) if match.image_score is not None else "N/A"
        )
        if match.distance_meters is not None:
            st.caption(f"Approximate distance: {match.distance_meters:.0f} m")
        if st.button("Arrange pickup", key=f"recover-{match.found_report_id}"):
            st.session_state["recovery_lost_id"] = match.lost_report_id
            st.session_state["recovery_found_id"] = match.found_report_id
            st.session_state["open_recovery"] = True
            st.rerun()
