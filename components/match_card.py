"""Potential-match component: show lost ↔ found pairing with score breakdown."""

from pathlib import Path

import streamlit as st

from models.schemas import MatchResult, Report
from services.matching_engine import TEXT_SCORE_FLOOR, gate_reason


def _percent(score: float) -> str:
    return f"{score:.0%}"


def _show_image(paths: tuple[str, ...], caption: str) -> None:
    for path in paths:
        if Path(path).is_file():
            st.image(path, caption=caption, width="stretch")
            return
    st.caption("No photo")


def _similarity_row(label: str, score: float | None, detail: str) -> None:
    if score is None:
        st.markdown(f"**{label}** — N/A")
        st.progress(0.0)
        st.caption(detail)
        return
    clamped = max(0.0, min(1.0, float(score)))
    st.markdown(f"**{label}** — {_percent(clamped)}")
    st.progress(clamped)
    st.caption(detail)


def render_lost_context(lost_report: Report) -> None:
    with st.container(border=True):
        st.markdown("**Matching this lost report**")
        _show_image(lost_report.image_paths, "Lost photo")
        st.write(lost_report.description)
        if lost_report.category:
            st.caption(f"Category: {lost_report.category}")


def render_match_card(
    match: MatchResult,
    found_report: Report | None = None,
    lost_report: Report | None = None,
    *,
    allow_pickup: bool = True,
) -> None:
    """Render one found candidate with side-by-side pairing and component scores."""
    with st.container(border=True):
        st.subheader(f"Overall match — {_percent(match.overall_score)}")

        lost_tab, found_tab = st.tabs(["Lost", "Found"])
        with lost_tab:
            if lost_report:
                _show_image(lost_report.image_paths, "Lost")
                st.write(lost_report.description)
                if lost_report.category:
                    st.caption(f"Category: {lost_report.category}")
            else:
                st.caption(f"id {match.lost_report_id[:8]}")
        with found_tab:
            if found_report:
                _show_image(found_report.image_paths, "Found")
                st.write(found_report.description)
                if found_report.category:
                    st.caption(f"Category: {found_report.category}")
                if found_report.holding_note:
                    st.caption(f"Where it is now: {found_report.holding_note}")
                if found_report.prefer_anonymous:
                    st.caption("Finder is anonymous")
            else:
                st.caption(f"id {match.found_report_id[:8]}")

        st.markdown("**Why this score**")
        _similarity_row("Text", match.text_score, "How similar the descriptions are")
        if match.image_score is not None:
            _similarity_row("Photos", match.image_score, "How similar the pictures are")
        else:
            st.caption("Photos not counted — no picture on one or both reports.")
        if match.category_score is not None:
            _similarity_row(
                "Category",
                match.category_score,
                "Same type of item required",
            )
        distance_note = "How close the map pins are"
        if match.distance_meters is not None:
            distance_note += f" · about {match.distance_meters:.0f} m apart"
        _similarity_row("Location", match.geo_score, distance_note)
        _similarity_row("Time", match.time_score, "How close the reported times are")

        reason = gate_reason(match.text_score, match.category_score)
        if reason:
            st.warning(f"Rejected: {reason}.")
        elif match.image_score is None:
            st.caption(
                f"Overall uses text, location, and time only "
                f"(text must be at least {TEXT_SCORE_FLOOR:.0%}). Photos did not lower this score."
            )
        else:
            st.caption(
                f"Blend of text, photos, location, and time "
                f"(text must be at least {TEXT_SCORE_FLOOR:.0%})."
            )

        if allow_pickup and st.button(
            "Arrange pickup",
            width="stretch",
            key=f"recover-{match.lost_report_id}-{match.found_report_id}",
        ):
            import page_defs

            st.session_state["recovery_lost_id"] = match.lost_report_id
            st.session_state["recovery_found_id"] = match.found_report_id
            st.switch_page(page_defs.recovery_page)
