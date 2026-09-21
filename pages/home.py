"""Landing page: report, match, then arrange pickup."""

import streamlit as st

import page_defs
from pages.account import current_user
from services.coordination import DEMO_PASSWORD


def render() -> None:
    st.title("Smart Lost & Found")
    st.subheader("Report an item, see likely matches, then agree on a public pickup.")

    user = current_user()
    if user:
        st.success(f"Signed in as **{user.display_name}** ({user.email}).")
    else:
        st.info(
            f"Log in on Account to attach reports to you. "
            f"Demo testers (Alex, Sam, Mia) all use password `{DEMO_PASSWORD}`."
        )

    lost_column, found_column, account_column = st.columns(3)
    if lost_column.button("I lost something", type="primary", width="stretch"):
        st.session_state["report_type"] = "lost"
        st.switch_page(page_defs.report_page)
    if found_column.button("I found something", width="stretch"):
        st.session_state["report_type"] = "found"
        st.switch_page(page_defs.report_page)
    if account_column.button("Account / demo login", width="stretch"):
        st.switch_page(page_defs.account_page)

    st.divider()
    step_one, step_two, step_three = st.columns(3)
    with step_one:
        st.markdown("**1. Report**")
        st.caption("Describe the item, drop optional photos, and pin likely places on the map.")
    with step_two:
        st.markdown("**2. Matches**")
        st.caption("Rank lost vs found using text, photos, location pins, and time.")
    with step_three:
        st.markdown("**3. Pickup**")
        st.caption("Share contact only if you want to, or stay anonymous and agree on a meetup.")
