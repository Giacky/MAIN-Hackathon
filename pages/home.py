"""Landing page: report, match, then arrange pickup."""

import streamlit as st

import page_defs
from pages.account import current_user
from services.coordination import DEMO_PASSWORD


def render() -> None:
    st.title("Smart Lost & Found")
    st.caption("Report an item, see likely matches, then agree on a public pickup.")

    user = current_user()
    if user:
        st.success(f"Signed in as **{user.display_name}**.")
    else:
        st.info(
            f"Log in on Account first. Demo logins Alex, Sam, and Mia all use "
            f"password `{DEMO_PASSWORD}`."
        )

    if st.button("I lost something", type="primary", width="stretch"):
        st.session_state["report_type"] = "lost"
        st.switch_page(page_defs.report_page)
    if st.button("I found something", width="stretch"):
        st.session_state["report_type"] = "found"
        st.switch_page(page_defs.report_page)
    if st.button("Account / demo login", width="stretch"):
        st.switch_page(page_defs.account_page)

    st.divider()
    st.markdown("**1. Report**")
    st.caption("Describe the item, add optional photos, and pin likely places on the map.")
    st.markdown("**2. Matches**")
    st.caption("Rank lost vs found using text, photos, location pins, and time.")
    st.markdown("**3. Pickup**")
    st.caption("Share contact only if you want to, or stay anonymous and agree on a meetup.")
