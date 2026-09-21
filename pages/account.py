"""Create an account, log in, and see your reports."""

import sqlite3

import streamlit as st

from database.repository import SQLiteRepository
from models.schemas import User
from services.auth import (
    SESSION_USER_KEY,
    hash_password,
    user_from_session,
    user_session_payload,
    verify_password,
)
from services.coordination import DEMO_ACCOUNTS, DEMO_PASSWORD, ensure_demo_handoff_reports


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def current_user() -> User | None:
    return user_from_session(st.session_state.get(SESSION_USER_KEY))


def render() -> None:
    repository = _repository()
    ensure_demo_handoff_reports(repository)
    user = current_user()

    st.title("Account")
    if user:
        st.success(f"Signed in as **{user.display_name}** ({user.email}).")
        my_reports = repository.list_reports_for_user(user.id)
        if my_reports:
            st.subheader("Your reports")
            for report in my_reports:
                st.write(
                    f"- {report.report_type.value.title()}: {report.description} "
                    f"({report.status.value})"
                )
        else:
            st.caption("You have not reported an item yet.")
        if st.button("Log out"):
            st.session_state.pop(SESSION_USER_KEY, None)
            st.rerun()
        return

    st.caption("Log in so lost and found items stay attached to you when you arrange pickup.")
    st.subheader("Dummy testers")
    st.caption(f"All three use password `{DEMO_PASSWORD}`. Open another browser to act as a second person.")
    for account in DEMO_ACCOUNTS:
        with st.container(border=True):
            label_column, button_column = st.columns([3, 1])
            label_column.markdown(
                f"**{account.display_name}** (`{account.email}`)\n\n{account.summary}"
            )
            if button_column.button("Log in", key=f"quick-login-{account.user_id}"):
                seeded = repository.get_user_by_email(account.email)
                if seeded is None:
                    st.error("Dummy user is missing. Reload the page.")
                else:
                    st.session_state[SESSION_USER_KEY] = user_session_payload(seeded)
                    st.rerun()

    login_tab, register_tab = st.tabs(["Log in", "Create account"])
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
