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
    """Demo-friendly row: label, progress bar, numeric similarity."""
    name_column, bar_column, value_column = st.columns([1.4, 3.2, 0.9])
    name_column.markdown(f"**{label}**")
    if score is None:
        bar_column.progress(0.0)
        value_column.markdown("**N/A**")
        st.caption(detail)
        return
    clamped = max(0.0, min(1.0, float(score)))
    bar_column.progress(clamped)
    value_column.markdown(f"**{_percent(clamped)}**")
    st.caption(f"{detail} · raw={clamped:.3f}")


def render_lost_context(lost_report: Report) -> None:
    """Show which lost report is being matched against."""
    with st.container(border=True):
        st.markdown("**Matching against this lost report**")
        left, right = st.columns([2, 1])
        with left:
            st.write(lost_report.description)
            if lost_report.category:
                st.caption(f"Category: {lost_report.category}")
        with right:
            _show_image(lost_report.image_paths, "Lost photo")


def render_match_card(
    match: MatchResult,
    found_report: Report | None = None,
    lost_report: Report | None = None,
) -> None:
    """Render one found candidate with side-by-side pairing and component scores."""
    with st.container(border=True):
        st.subheader(f"Overall match — {_percent(match.overall_score)}")

        lost_column, found_column = st.columns(2)
        with lost_column:
            st.markdown("**Lost**")
            if lost_report:
                st.write(lost_report.description)
                if lost_report.category:
                    st.caption(f"Category: {lost_report.category}")
                _show_image(lost_report.image_paths, "Lost")
            else:
                st.caption(f"id {match.lost_report_id[:8]}")

        with found_column:
            st.markdown("**Found (candidate)**")
            if found_report:
                st.write(found_report.description)
                if found_report.category:
                    st.caption(f"Category: {found_report.category}")
                _show_image(found_report.image_paths, "Found")
            else:
                st.caption(f"id {match.found_report_id[:8]}")

        st.markdown("**Component similarities**")
        _similarity_row(
            "Text (BGE) · 60%",
            match.text_score,
            "Description embedding cosine similarity (primary signal)",
        )
        if match.image_score is not None:
            _similarity_row(
                "Image (CLIP) · 28%",
                match.image_score,
                "Photo embedding cosine similarity (max pairwise)",
            )
        else:
            _similarity_row(
                "Image (CLIP) · 28%",
                None,
                "Not used — need saved photos on both sides (weight redistributed)",
            )
        if match.category_score is not None:
            _similarity_row(
                "Category (gate)",
                match.category_score,
                "Hard gate: different category → overall 0%",
            )
        else:
            _similarity_row(
                "Category (gate)",
                None,
                "No category on both sides — gate skipped",
            )
        distance_note = "Haversine vs search radius (tie-breaker only)" + (
            f" · ≈ {match.distance_meters:.0f} m apart"
            if match.distance_meters is not None
            else ""
        )
        _similarity_row("Location · 8%", match.geo_score, distance_note)
        _similarity_row(
            "Time · 4%",
            match.time_score,
            "Event-time proximity (tie-breaker only)",
        )

        reason = gate_reason(match.text_score, match.category_score)
        if reason:
            st.warning(
                f"Overall **{_percent(match.overall_score)}** — rejected by {reason}. "
                "Location/time were not allowed to rescue this pair."
            )
        else:
            st.info(
                f"Overall **{_percent(match.overall_score)}** = weighted blend "
                f"(text 60%, image 28%, location 8%, time 4%) after gates "
                f"(same category if labeled; text ≥ {TEXT_SCORE_FLOOR:.0%})."
            )
        if st.button("Arrange pickup", key=f"recover-{match.found_report_id}"):
            st.session_state["recovery_lost_id"] = match.lost_report_id
            st.session_state["recovery_found_id"] = match.found_report_id
            st.session_state["open_recovery"] = True
            st.rerun()
