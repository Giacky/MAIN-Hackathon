"""Mock match results for independent UI development."""

import streamlit as st

from components.match_card import render_match_card
from database.repository import SQLiteRepository
from models.schemas import MatchResult, Report, ReportType
from services.coordination import (
    DEMO_FOUND_HOTEL_ID,
    DEMO_FOUND_LIBRARY_ID,
    DEMO_LOST_ID,
    ensure_demo_handoff_reports,
)


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


def render() -> None:
    st.title("Potential matches")
    st.caption("Demo data only. The matching engine will replace these examples.")
    ensure_demo_handoff_reports(_repository())
    for match, report in _demo_matches():
        render_match_card(match, report)
