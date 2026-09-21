"""Match results for the signed-in user, with demo pairs as a fallback."""

import streamlit as st

from components.match_card import render_match_card
from database.repository import SQLiteRepository
from models.schemas import MatchResult, Report, ReportType
from pages.account import current_user
from services.coordination import (
    DEMO_FOUND_HOTEL_ID,
    DEMO_FOUND_LIBRARY_ID,
    DEMO_LOST_ID,
    ensure_demo_handoff_reports,
)
from services.matching_engine import MatchingEngine


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def _demo_matches() -> list[tuple[MatchResult, Report]]:
    lost_id = DEMO_LOST_ID
    return [
        (
            MatchResult(
                lost_report_id=lost_id,
                found_report_id=DEMO_FOUND_LIBRARY_ID,
                overall_score=0.91,
                text_score=0.94,
                image_score=None,
                geo_score=0.88,
                time_score=0.79,
                distance_meters=240.0,
            ),
            Report(
                id=DEMO_FOUND_LIBRARY_ID,
                report_type=ReportType.FOUND,
                description="Black wallet found near the university library.",
                category="Wallet",
                prefer_anonymous=True,
            ),
        ),
        (
            MatchResult(
                lost_report_id=lost_id,
                found_report_id=DEMO_FOUND_HOTEL_ID,
                overall_score=0.73,
                text_score=0.81,
                image_score=None,
                geo_score=0.72,
                time_score=0.65,
                distance_meters=860.0,
            ),
            Report(
                id=DEMO_FOUND_HOTEL_ID,
                report_type=ReportType.FOUND,
                description="Dark card holder left at a hotel reception.",
                category="Wallet",
                prefer_anonymous=True,
            ),
        ),
    ]


def _matches_for_user(user_id: str) -> list[tuple[MatchResult, Report]]:
    repository = _repository()
    mine = repository.list_reports_for_user(user_id)
    everyone = repository.list_reports()
    engine = MatchingEngine()
    cards: list[tuple[MatchResult, Report]] = []

    my_lost = [report for report in mine if report.report_type is ReportType.LOST]
    other_found = [
        report
        for report in everyone
        if report.report_type is ReportType.FOUND
        and report.user_id
        and report.user_id != user_id
    ]
    for lost in my_lost:
        for match in engine.rank_matches(lost, other_found):
            found = repository.get_report(match.found_report_id)
            if found:
                cards.append((match, found))

    my_found = [report for report in mine if report.report_type is ReportType.FOUND]
    other_lost = [
        report
        for report in everyone
        if report.report_type is ReportType.LOST
        and report.user_id
        and report.user_id != user_id
    ]
    for found in my_found:
        for lost in other_lost:
            for match in engine.rank_matches(lost, [found]):
                cards.append((match, found))

    return cards


def render() -> None:
    st.title("Potential matches")
    repository = _repository()
    ensure_demo_handoff_reports(repository)
    user = current_user()

    if user:
        st.caption(f"Matches involving {user.display_name}'s reports.")
        mine = repository.list_reports_for_user(user.id)
        if mine:
            st.write("**Your items**")
            for report in mine:
                st.write(f"- {report.report_type.value.title()}: {report.description}")
        cards = _matches_for_user(user.id)
        if not cards:
            st.info("No other reports to match yet. Demo pairs are shown below.")
            cards = _demo_matches()
        for match, report in cards:
            render_match_card(match, report)
        return

    st.caption("Demo data. Log in to see matches for your own reports.")
    for match, report in _demo_matches():
        render_match_card(match, report)
