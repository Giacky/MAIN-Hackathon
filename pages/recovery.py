"""Placeholder recovery, chat, and drop-off experience."""

import streamlit as st


def render() -> None:
    st.title("Recovery")
    st.caption("Static examples only; no real-time communication is implemented.")

    chat_column, drop_off_column = st.columns(2)
    with chat_column:
        st.subheader("Chat")
        with st.container(border=True):
            st.chat_message("user").write("I think this may be my wallet.")
            st.chat_message("assistant").write("Can you describe the card inside?")
            st.text_input("Message", placeholder="Chat integration coming soon", disabled=True)

    with drop_off_column:
        st.subheader("Item dropped off at…")
        with st.container(border=True):
            st.markdown("### Hotel Reception")
            st.write("Ask reception for item #123.")
            st.caption("Drop-off coordinates and collection details will appear here.")

    st.button("Mark item as recovered", disabled=True, help="Persistence hookup pending")
