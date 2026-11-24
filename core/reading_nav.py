import streamlit as st


def open_test(test_id: str) -> None:
    st.session_state["reading_test"] = test_id
    st.session_state["reading_opens"] = st.session_state.get("reading_opens", 0) + 1


def close_test() -> None:
    st.session_state["reading_test"] = None
