"""Rank lost and found reports, then open pickup for a pair."""

import streamlit as st

from components.match_card import render_lost_context, render_match_card
from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from pages.account import current_user
from services.demo_seed import seed_demo_reports
from services.matching_engine import MatchingEngine
from utils.config import DATABASE_PATH


def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def _engine() -> MatchingEngine:
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
    owner = "you" if st.session_state.get("_matches_user_id") == report.user_id else ""
    prefix = f"[{_report_type_value(report)}]"
    if owner:
        prefix += " yours"
    return f"{prefix} {preview}"


def _split_open_reports() -> tuple[list[Report], list[Report]]:
    reports = _repository().list_open_reports()
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
    with st.expander("Demo tools", expanded=False):
        st.caption(f"Database: `{DATABASE_PATH}`")
        if st.button("Reload demo users + sample reports", width="stretch"):
            lost_reports, _found = seed_demo_reports()
            st.cache_resource.clear()
            st.session_state["demo_lost_id"] = lost_reports[0].id
            st.success("Reloaded Alex, Sam, Mia and their sample items.")
            st.rerun()


def _persist(matches) -> None:
    repository = _repository()
    for match in matches:
        repository.save_match(match)


def _render_lost_tab(lost_reports: list[Report], found_reports: list[Report], user) -> None:
    if not lost_reports or not found_reports:
        st.warning("Need at least one open lost report and one found report.")
        return

    default_index = 0
    demo_lost_id = st.session_state.get("demo_lost_id")
    if demo_lost_id:
        for index, report in enumerate(lost_reports):
            if report.id == demo_lost_id:
                default_index = index
                break
    elif user:
        for index, report in enumerate(lost_reports):
            if report.user_id == user.id:
                default_index = index
                break

    selected_index = st.selectbox(
        "Lost item",
        options=list(range(len(lost_reports))),
        index=min(default_index, len(lost_reports) - 1),
        format_func=lambda index: _label(lost_reports[index]),
    )
    selected = lost_reports[selected_index]
    render_lost_context(selected)

    other_found = [
        report
        for report in found_reports
        if not (selected.user_id and report.user_id == selected.user_id)
    ]
    with st.spinner("Ranking found reports…"):
        matches = _engine().rank_matches(selected, other_found)
    _persist(matches)

    strong = [match for match in matches if match.overall_score > 0]
    weak = [match for match in matches if match.overall_score <= 0]
    found_by_id = {report.id: report for report in other_found}

    if not strong:
        st.info("No likely found items for this report.")
    for match in strong:
        render_match_card(
            match,
            found_by_id.get(match.found_report_id),
            lost_report=selected,
        )
    if weak:
        with st.expander(f"Unlikely matches ({len(weak)})"):
            for match in weak:
                render_match_card(
                    match,
                    found_by_id.get(match.found_report_id),
                    lost_report=selected,
                    allow_pickup=False,
                )


def _render_found_tab(lost_reports: list[Report], found_reports: list[Report], user) -> None:
    if not lost_reports or not found_reports:
        st.warning("Need at least one open lost report and one found report.")
        return

    default_index = 0
    if user:
        for index, report in enumerate(found_reports):
            if report.user_id == user.id:
                default_index = index
                break

    selected_index = st.selectbox(
        "Found item",
        options=list(range(len(found_reports))),
        index=min(default_index, len(found_reports) - 1),
        format_func=lambda index: _label(found_reports[index]),
        key="found-item-select",
    )
    selected_found = found_reports[selected_index]
    other_lost = [
        report
        for report in lost_reports
        if not (selected_found.user_id and report.user_id == selected_found.user_id)
    ]

    ranked: list = []
    engine = _engine()
    for lost in other_lost:
        matches = engine.rank_matches(lost, [selected_found])
        if matches:
            ranked.append((matches[0], lost))
    ranked.sort(key=lambda pair: pair[0].overall_score, reverse=True)
    _persist([match for match, _lost in ranked])

    strong = [(match, lost) for match, lost in ranked if match.overall_score > 0]
    if not strong:
        st.info("No likely lost items for this find.")
        return
    for match, lost in strong:
        render_match_card(match, selected_found, lost_report=lost)


def render() -> None:
    st.title("Matches")
    st.caption("Compare a lost report with found reports using text, photos, map pins, and time.")

    user = current_user()
    st.session_state["_matches_user_id"] = user.id if user else None
    if user:
        st.caption(f"Signed in as {user.display_name}. Pickup stays on your account.")
    else:
        st.caption("Log in so pickup can tell which side of the match you are.")

    lost_reports, found_reports = _split_open_reports()
    view = st.radio(
        "I want to match",
        ["a lost item", "a found item"],
        horizontal=True,
        key="matches_side",
    )
    if view == "a lost item":
        _render_lost_tab(lost_reports, found_reports, user)
    else:
        _render_found_tab(lost_reports, found_reports, user)

    _render_debug_tools()
