"""st.Page objects shared so other modules can call st.switch_page."""

import streamlit as st

home_page: st.Page | None = None
report_page: st.Page | None = None
matches_page: st.Page | None = None
map_page: st.Page | None = None
recovery_page: st.Page | None = None
account_page: st.Page | None = None


def init() -> None:
    global home_page, report_page, matches_page, map_page, recovery_page, account_page
    from pages.account import render as render_account
    from pages.home import render as render_home
    from pages.map_view import render as render_map
    from pages.matches import render as render_matches
    from pages.recovery import render as render_recovery
    from pages.report_item import render as render_report_item

    home_page = st.Page(render_home, title="Home", icon="🏠", url_path="home", default=True)
    report_page = st.Page(
        render_report_item, title="Report item", icon="📝", url_path="report-item"
    )
    matches_page = st.Page(render_matches, title="Matches", icon="🧩", url_path="matches")
    map_page = st.Page(render_map, title="Map", icon="🗺️", url_path="map")
    recovery_page = st.Page(
        render_recovery, title="Pickup", icon="🤝", url_path="recovery"
    )
    account_page = st.Page(
        render_account, title="Account", icon="👤", url_path="sign-in"
    )


def all_pages() -> list[st.Page]:
    assert home_page and report_page and matches_page
    assert map_page and recovery_page and account_page
    return [
        home_page,
        report_page,
        matches_page,
        map_page,
        recovery_page,
        account_page,
    ]
