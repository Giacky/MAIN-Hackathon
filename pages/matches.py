"""Rank stored found reports against a selected lost report."""

import streamlit as st

from components.match_card import render_lost_context, render_match_card
from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from services.demo_seed import seed_demo_reports
from services.matching_engine import MatchingEngine
from utils.config import DATABASE_PATH


def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def _engine() -> MatchingEngine:
    # Fresh instance each run — cached engines keep stale methods after Streamlit reload.
    return MatchingEngine()


def _report_type_value(report: Report) -> str:
    report_type = report.report_type
    if isinstance(report_type, ReportType):
        return report_type.value
    return str(report_type).lower()


def _label(report: Report) -> str:
    preview = report.description.strip().replace("\n", " ")
    if len(preview) > 72:
        preview = preview[:69] + "..."
    return f"[{_report_type_value(report)}] {preview} ({report.id[:8]})"


def _split_reports() -> tuple[list[Report], list[Report]]:
    reports = _repository().list_reports()
    lost_reports = [
        report
        for report in reports
        if _report_type_value(report) == ReportType.LOST.value
    ]
    found_reports = [
        report
        for report in reports
        if _report_type_value(report) == ReportType.FOUND.value
    ]
    return lost_reports, found_reports


def _render_debug_tools() -> None:
    st.divider()
    with st.expander("Demo / debug tools", expanded=False):
        st.caption(f"Database: `{DATABASE_PATH}`")
        if st.button(
            "Reset DB → 2 lost + 4 found",
            key="debug-reset-db",
            width="stretch",
        ):
            lost_reports, _found = seed_demo_reports()
            st.cache_resource.clear()
            st.session_state["demo_lost_id"] = lost_reports[0].id
            st.success("Seeded 2 lost and 4 found sample reports.")
            st.rerun()
        if st.button("Clear Streamlit caches", key="debug-clear-cache", width="stretch"):
            st.cache_resource.clear()
            st.cache_data.clear()
            st.success("Caches cleared.")
            st.rerun()


def render() -> None:
    st.title("Potential matches")
    st.caption("Ranked by text, location, time, and images when both sides have photos.")

    # One-time cache bust after the enum/hot-reload matching bug.
    if not st.session_state.get("_matches_cache_busted"):
        st.cache_resource.clear()
        st.session_state["_matches_cache_busted"] = True

    lost_reports, found_reports = _split_reports()

    if not lost_reports or not found_reports:
        st.warning(
            "Need at least one lost and one found report. "
            "Open the debug tools at the bottom to seed demo data."
        )
        _render_debug_tools()
        return

    st.caption(
        f"**{len(lost_reports)} lost · {len(found_reports)} found** in `{DATABASE_PATH.name}`"
    )

    demo_lost_id = st.session_state.get("demo_lost_id")
    default_index = 0
    if demo_lost_id:
        for index, report in enumerate(lost_reports):
            if report.id == demo_lost_id:
                default_index = index
                break

    selected_index = st.selectbox(
        "Lost item to match",
        options=list(range(len(lost_reports))),
        index=min(default_index, len(lost_reports) - 1),
        format_func=lambda index: _label(lost_reports[index]),
    )
    selected = lost_reports[selected_index]
    render_lost_context(selected)

    try:
        with st.spinner("Scoring found reports (text / location / time / image)…"):
            matches = _engine().rank_matches(selected, found_reports)
    except Exception as exc:
        st.error(f"Matching failed: {exc}")
        st.caption(
            f"Selected report_type={_report_type_value(selected)!r} id={selected.id[:8]}"
        )
        _render_debug_tools()
        return

    found_by_id = {report.id: report for report in found_reports}
    if not matches:
        st.warning("No found reports could be scored.")
        _render_debug_tools()
        return

    st.markdown(f"### Ranked found reports ({len(matches)})")
    st.caption(
        "Each card pairs your lost item with one found item. "
        "Scores use **text + location + time**, and **image** when both reports have photos."
    )
    for match in matches:
        render_match_card(
            match,
            found_by_id.get(match.found_report_id),
            lost_report=selected,
        )

    _render_debug_tools()
