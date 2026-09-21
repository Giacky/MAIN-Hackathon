"""Match handoff: optional contact, finder anonymity, and meetup agreement."""

from datetime import datetime, timedelta

import streamlit as st

import page_defs
from database.repository import SQLiteRepository
from models.schemas import (
    ChatMessage,
    Meetup,
    MeetupStatus,
    Report,
    as_utc,
    match_thread_id,
)
from pages.account import current_user
from utils.ui import page_footer_nav, page_header
from services.coordination import (
    can_respond_to_meetup,
    contact_for_viewer,
    display_name_for_sender,
    is_own_report,
    role_for_user,
)

MEETUP_PRESETS = [
    "University library entrance",
    "Hotel reception",
    "Student service desk",
    "Other (type below)",
]


@st.cache_resource
def _repository() -> SQLiteRepository:
    return SQLiteRepository()


def _own_report(lost: Report, found: Report, role: str) -> Report:
    return lost if role == "lost" else found


def _other_report(lost: Report, found: Report, role: str) -> Report:
    return found if role == "lost" else lost


def _format_contact(email: str | None, phone: str | None) -> None:
    if email:
        st.write(f"Email: {email}")
    if phone:
        st.write(f"Phone: {phone}")
    if not email and not phone:
        st.caption("No email or phone on file.")


def _render_other_contact(other: Report, role: str) -> None:
    st.subheader("Their contact")
    email, phone = contact_for_viewer(other, role)
    if other.prefer_anonymous and not is_own_report(other, role):
        st.info(
            "The other person is staying anonymous. Agree on a public meetup instead."
        )
        return
    _format_contact(email, phone)


def _render_my_contact(own: Report, role: str) -> None:
    st.subheader("Your contact")
    if role == "found":
        st.caption("You can stay anonymous. The owner can still propose a public meetup.")
    else:
        st.caption("Sharing contact is optional. A meetup works either way.")

    email = st.text_input("Email", value=own.contact_email or "", key=f"own-email-{role}")
    phone = st.text_input("Phone", value=own.contact_phone or "", key=f"own-phone-{role}")
    anonymous_label = (
        "Stay anonymous" if role == "found" else "Hide my contact from the other person"
    )
    prefer_anonymous = st.checkbox(
        anonymous_label,
        value=own.prefer_anonymous,
        key=f"own-anon-{role}",
    )
    if st.button("Save contact settings", key=f"save-contact-{role}"):
        own.contact_email = email.strip() or None
        own.contact_phone = phone.strip() or None
        own.prefer_anonymous = prefer_anonymous
        _repository().add_report(own)
        st.success("Saved.")
        st.rerun()


def _render_meetup(match_id: str, role: str) -> None:
    st.subheader("Meetup")
    meetup = _repository().get_meetup(match_id)
    if meetup is None:
        st.caption("Propose a public place and time. Nobody has to share a home address.")
    elif meetup.status is MeetupStatus.ACCEPTED:
        st.success(
            f"Agreed: {meetup.location_name} at "
            f"{meetup.meeting_time.strftime('%a %d %b, %H:%M')}."
        )
    elif meetup.status is MeetupStatus.DECLINED:
        st.warning(
            f"Last proposal ({meetup.location_name}) was declined. Suggest another option."
        )
    else:
        proposer = "you" if meetup.proposed_by == role else "the other person"
        st.info(
            f"{proposer.capitalize()} proposed **{meetup.location_name}** on "
            f"{meetup.meeting_time.strftime('%a %d %b, %H:%M')}."
        )
        if can_respond_to_meetup(meetup, role):
            if st.button("Accept meetup", type="primary", width="stretch"):
                _repository().update_meetup_status(match_id, MeetupStatus.ACCEPTED)
                st.rerun()
            if st.button("Decline", width="stretch"):
                _repository().update_meetup_status(match_id, MeetupStatus.DECLINED)
                st.rerun()

    with st.form("meetup-proposal"):
        preset = st.selectbox("Place", MEETUP_PRESETS)
        custom = st.text_input("Custom place", placeholder="Cafe on the corner, ...")
        meeting_date = st.date_input("Date", value=datetime.now().date())
        meeting_time = st.time_input(
            "Time",
            value=(datetime.now() + timedelta(hours=2)).time().replace(
                second=0, microsecond=0
            ),
        )
        submitted = st.form_submit_button("Propose meetup")

    if submitted:
        location = custom.strip() if preset.startswith("Other") else preset
        if preset.startswith("Other") and not location:
            st.error("Type a custom place, or pick a preset location.")
            return
        _repository().save_meetup(
            Meetup(
                match_id=match_id,
                proposed_by=role,
                location_name=location,
                meeting_time=as_utc(datetime.combine(meeting_date, meeting_time)),
            )
        )
        st.rerun()


def _render_notes(match_id: str, role: str) -> None:
    st.subheader("Short notes")
    st.caption("Optional. Use the meetup card for time and place.")
    for message in _repository().list_chat_messages(match_id):
        speaker = display_name_for_sender(message.sender, role)
        with st.chat_message("user" if message.sender == role else "assistant"):
            st.write(f"**{speaker}:** {message.message}")
    note = st.chat_input("Add a short note")
    if note and note.strip():
        _repository().add_chat_message(
            ChatMessage(match_id=match_id, sender=role, message=note.strip())
        )
        st.rerun()


def _selected_pair(repository: SQLiteRepository) -> tuple[str | None, str | None]:
    lost_id = st.session_state.get("recovery_lost_id")
    found_id = st.session_state.get("recovery_found_id")
    query_lost = st.query_params.get("lost")
    query_found = st.query_params.get("found")
    if query_lost:
        lost_id = query_lost if isinstance(query_lost, str) else query_lost[0]
    if query_found:
        found_id = query_found if isinstance(query_found, str) else query_found[0]
    if lost_id and found_id:
        return str(lost_id), str(found_id)

    matches = repository.list_matches()
    if matches:
        top = matches[0]
        return top.lost_report_id, top.found_report_id
    return None, None


def render() -> None:
    page_header(back_page=page_defs.matches_page, back_label="Back to Matches")
    page_footer_nav(current="pickup")
    repository = _repository()
    lost_id, found_id = _selected_pair(repository)
    if not lost_id or not found_id:
        st.title("Arrange pickup")
        st.info("Open a match and choose Arrange pickup.")
        if st.button("Go to Matches", type="primary"):
            st.switch_page(page_defs.matches_page)
        return

    st.session_state["recovery_lost_id"] = lost_id
    st.session_state["recovery_found_id"] = found_id
    lost = repository.get_report(lost_id)
    found = repository.get_report(found_id)
    if lost is None or found is None:
        st.title("Arrange pickup")
        st.error("That match is no longer in the database.")
        if st.button("Go to Matches"):
            st.switch_page(page_defs.matches_page)
        return

    st.title("Arrange pickup")
    st.caption(
        "Share contact only if both people want to. Finders can stay anonymous "
        "and still agree on a public meetup."
    )

    user = current_user()
    inferred_role = role_for_user(
        user.id if user else None,
        lost,
        found,
        email=user.email if user else None,
    )
    if user and inferred_role:
        role = inferred_role
        side = "lost this item" if role == "lost" else "found this item"
        st.info(f"Signed in as **{user.display_name}**. You {side}.")
    elif user:
        st.warning(
            "This match is not linked to your account. "
            "Log in as the owner or finder, or open one of your own matches."
        )
        if st.button("Go to Account"):
            st.switch_page(page_defs.account_page)
        return
    else:
        st.warning("Log in so this page stays on your lost or found report.")
        if st.button("Go to Account", type="primary"):
            st.switch_page(page_defs.account_page)
        return

    st.write(f"**Lost:** {lost.description}")
    st.write(f"**Found:** {found.description}")
    if found.holding_note:
        st.info(f"Finder note: {found.holding_note}")

    contact_tab, meetup_tab = st.tabs(["Contact", "Meetup"])
    with contact_tab:
        with st.container(border=True):
            _render_other_contact(_other_report(lost, found, role), role)
        with st.container(border=True):
            _render_my_contact(_own_report(lost, found, role), role)
    with meetup_tab:
        with st.container(border=True):
            _render_meetup(match_thread_id(lost.id, found.id), role)

    match_id = match_thread_id(lost.id, found.id)
    _render_notes(match_id, role)

    meetup = repository.get_meetup(match_id)
    recovered = lost.status.value == "recovered" or found.status.value == "recovered"
    if recovered:
        st.success("This item is marked recovered.")
        return
    if st.button("Mark item as recovered", type="primary"):
        repository.mark_recovered(lost.id)
        repository.mark_recovered(found.id)
        st.rerun()
    if meetup is None or meetup.status is not MeetupStatus.ACCEPTED:
        st.caption("You can mark it recovered after pickup, even if no meetup was accepted.")
