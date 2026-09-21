"""Rank your lost or found reports against other people's items."""

import streamlit as st

from components.item_card import render_item_tile
from components.match_card import render_lost_context, render_match_card
from database.repository import SQLiteRepository
from models.schemas import Report, ReportType
from pages.account import current_user
from services.demo_seed import seed_demo_reports
from services.matching_engine import MatchingEngine
from utils.config import DATABASE_PATH
from utils.ui import page_nav


def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def _engine() -> MatchingEngine:
    return MatchingEngine()


def _report_type_value(report: Report) -> str:
    report_type = report.report_type
    if isinstance(report_type, ReportType):
        return report_type.value
    return str(report_type).lower()


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


def _mine(reports: list[Report], user_id: str) -> list[Report]:
    return [report for report in reports if report.user_id == user_id]


def _render_debug_tools() -> None:
    st.divider()
    with st.expander("Demo tools", expanded=False):
        st.caption(f"Database: `{DATABASE_PATH}`")
        if st.button("Reload demo users + sample reports", width="stretch"):
            seed_demo_reports()
            st.cache_resource.clear()
            st.success("Reloaded Alex, Sam, Mia and their sample items.")
            st.rerun()


def _persist(matches) -> None:
    repository = _repository()
    for match in matches:
        repository.save_match(match)


def _pick_own_report(reports: list[Report], session_key: str, heading: str) -> Report | None:
    if not reports:
        return None
    ids = {report.id for report in reports}
    selected_id = st.session_state.get(session_key)
    if selected_id not in ids:
        selected_id = reports[0].id
        st.session_state[session_key] = selected_id

    st.markdown(f"**{heading}**")
    st.caption("Tap one item to rank it against other people's reports.")
    for row_start in range(0, len(reports), 2):
        row = reports[row_start : row_start + 2]
        columns = st.columns(len(row))
        for column, report in zip(columns, row):
            with column:
                if render_item_tile(
                    report,
                    selected=report.id == selected_id,
                    button_key=f"{session_key}-tile-{report.id}",
                ):
                    st.session_state[session_key] = report.id
                    st.rerun()

    return next(report for report in reports if report.id == selected_id)


def _render_lost_matches(my_lost: list[Report], found_reports: list[Report], user) -> None:
    if not my_lost:
        st.info("You have no open lost reports yet. Report a lost item first.")
        return
    if not found_reports:
        st.warning("No open found reports to compare against.")
        return

    selected = _pick_own_report(my_lost, "matches_selected_lost_id", "Your lost items")
    if selected is None:
        return
    render_lost_context(selected)

    other_found = [
        report for report in found_reports if report.user_id != user.id
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


def _render_found_matches(lost_reports: list[Report], my_found: list[Report], user) -> None:
    if not my_found:
        st.info("You have no open found reports yet. Report a found item first.")
        return
    if not lost_reports:
        st.warning("No open lost reports to compare against.")
        return

    selected_found = _pick_own_report(
        my_found, "matches_selected_found_id", "Your found items"
    )
    if selected_found is None:
        return
    other_lost = [report for report in lost_reports if report.user_id != user.id]

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
    page_nav()
    st.title("Matches")
    st.caption("Pick one of your items, then see likely matches from other people.")

    user = current_user()
    if user is None:
        st.warning("Log in to see matches for your own lost and found items.")
        return

    st.caption(f"Signed in as {user.display_name}.")
    lost_reports, found_reports = _split_open_reports()
    my_lost = _mine(lost_reports, user.id)
    my_found = _mine(found_reports, user.id)

    lost_label = f"Lost ({len(my_lost)})"
    found_label = f"Found ({len(my_found)})"
    prefer_found = bool(st.session_state.pop("matches_prefer_found", False))
    show_found_first = prefer_found or (bool(my_found) and not my_lost)

    if show_found_first:
        found_tab, lost_tab = st.tabs([found_label, lost_label])
        with found_tab:
            _render_found_matches(lost_reports, my_found, user)
        with lost_tab:
            _render_lost_matches(my_lost, found_reports, user)
    else:
        lost_tab, found_tab = st.tabs([lost_label, found_label])
        with lost_tab:
            _render_lost_matches(my_lost, found_reports, user)
        with found_tab:
            _render_found_matches(lost_reports, my_found, user)

    _render_debug_tools()
