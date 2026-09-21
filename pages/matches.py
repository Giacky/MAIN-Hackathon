"""Mock match results for independent UI development."""

import streamlit as st

from components.match_card import render_match_card
from models.schemas import MatchResult, Report, ReportType


def _demo_matches() -> list[tuple[MatchResult, Report]]:
    lost_id = "lost-demo-123"
    return [
        (
            MatchResult(
                lost_report_id=lost_id,
                found_report_id="found-demo-456",
                overall_score=0.91,
                text_score=0.94,
                image_score=None,
                geo_score=0.88,
                time_score=0.79,
                distance_meters=240.0,
            ),
            Report(
                id="found-demo-456",
                report_type=ReportType.FOUND,
                description="Black wallet found near the university library.",
                category="Wallet",
            ),
        ),
        (
            MatchResult(
                lost_report_id=lost_id,
                found_report_id="found-demo-789",
                overall_score=0.73,
                text_score=0.81,
                image_score=None,
                geo_score=0.72,
                time_score=0.65,
                distance_meters=860.0,
            ),
            Report(
                id="found-demo-789",
                report_type=ReportType.FOUND,
                description="Dark card holder left at a hotel reception.",
                category="Wallet",
            ),
        ),
    ]


def render() -> None:
    st.title("Potential matches")
    st.caption("Demo data only. The matching engine will replace these examples.")
    for match, report in _demo_matches():
        render_match_card(match, report)
