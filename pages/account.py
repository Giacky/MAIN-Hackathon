"""Create an account, log in, and see your reports."""

import sqlite3

import streamlit as st

import page_defs
from components.item_card import render_item_card
from database.repository import SQLiteRepository
from models.schemas import User
from services.auth import (
    SESSION_USER_KEY,
    hash_password,
    user_from_session,
    user_session_payload,
    verify_password,
)
from services.coordination import DEMO_ACCOUNTS, DEMO_PASSWORD
from utils.ui import page_nav


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def current_user() -> User | None:
    return user_from_session(st.session_state.get(SESSION_USER_KEY))


def _login_as(repository: SQLiteRepository, email: str) -> None:
    seeded = repository.get_user_by_email(email)
    if seeded is None:
        st.error("Dummy user is missing. Reload the app from Home.")
        return
    st.session_state[SESSION_USER_KEY] = user_session_payload(seeded)
    st.rerun()


def render() -> None:
    repository = _repository()
    user = current_user()

    page_nav()
    st.title("Account")
    if user:
        st.success(f"Signed in as **{user.display_name}** ({user.email}).")
        my_reports = repository.list_reports_for_user(user.id)
        if my_reports:
            st.subheader("Your reports")
            for report in my_reports:
                render_item_card(report)
        else:
            st.caption("You have not reported an item yet.")
        if st.button("Report an item", type="primary", width="stretch"):
            st.switch_page(page_defs.report_page)
        if st.button("See matches", width="stretch"):
            st.switch_page(page_defs.matches_page)
        if st.button("Log out", width="stretch"):
            st.session_state.pop(SESSION_USER_KEY, None)
            st.rerun()
        return

    st.caption("Log in so lost and found items stay attached to you when you arrange pickup.")
    demo_tab, login_tab, register_tab = st.tabs(["Demo people", "Log in", "Create account"])

    with demo_tab:
        st.caption(f"Password for all three: `{DEMO_PASSWORD}`.")
        for account in DEMO_ACCOUNTS:
            if st.button(
                f"{account.display_name} — {account.summary}",
                width="stretch",
                key=f"quick-login-{account.user_id}",
            ):
                _login_as(repository, account.email)

    with login_tab:
        with st.form("login-form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            account = repository.get_user_by_email(email)
            if account is None or not verify_password(password, account.password_hash):
                st.error("Unknown email or incorrect password.")
            else:
                st.session_state[SESSION_USER_KEY] = user_session_payload(account)
                st.rerun()

    with register_tab:
        with st.form("register-form"):
            display_name = st.text_input("Name")
            email = st.text_input("Email", key="register-email")
            password = st.text_input("Password", type="password", key="register-password")
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            if not display_name.strip() or not email.strip() or len(password) < 4:
                st.error("Name, email, and a password of at least 4 characters are required.")
                return
            if repository.get_user_by_email(email):
                st.error("That email already has an account. Log in instead.")
                return
            try:
                account = repository.add_user(
                    User(
                        email=email.strip().lower(),
                        display_name=display_name.strip(),
                        password_hash=hash_password(password),
                    )
                )
            except sqlite3.IntegrityError:
                st.error("That email already has an account. Log in instead.")
                return
            st.session_state[SESSION_USER_KEY] = user_session_payload(account)
            st.rerun()
