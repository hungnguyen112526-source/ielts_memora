"""Streamlit-side login state: who is signed in, login/register forms, persistent cookie."""
from __future__ import annotations

import streamlit as st

from . import auth
from .reader_component import cookie_bridge

COOKIE_NAME = "memora_session"


def _read_cookie() -> str | None:
    try:
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:          # old Streamlit without st.context, or no request context
        return None


def current_user() -> dict | None:
    """Signed-in user for this browser session. After a page refresh the cookie
    token restores the login (Streamlit itself forgets session_state on refresh)."""
    user = st.session_state.get("user")
    if user:
        return user
    if st.session_state.get("_cookie_cleared"):      # just logged out in this session
        return None
    token = _read_cookie()
    user = auth.user_from_token(token)
    if user:
        st.session_state["user"] = user
        st.session_state["_session_token"] = token
        st.session_state["_cookie_token"] = token
    return user


def sync_cookie() -> None:
    """Render the invisible cookie component when the cookie needs setting/clearing."""
    token = st.session_state.get("_cookie_token")
    if token:
        cookie_bridge("set", COOKIE_NAME, token, auth.SESSION_DAYS)
    elif st.session_state.get("_cookie_cleared"):
        cookie_bridge("clear", COOKIE_NAME)


def _sign_in(user: dict) -> None:
    token = auth.create_session(user["id"])
    for k in ("reading_test", "reading_opens", "_cookie_cleared"):
        st.session_state.pop(k, None)
    st.session_state["user"] = user
    st.session_state["_session_token"] = token
    st.session_state["_cookie_token"] = token


def logout() -> None:
    auth.delete_session(st.session_state.get("_session_token") or _read_cookie())
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state["_cookie_cleared"] = True      # makes the browser drop the cookie
    st.rerun()


def login_view() -> None:
    """Login / register screen (shown by app.py whenever nobody is signed in)."""
    left, mid, right = st.columns([1, 1.4, 1])
    with mid:
        st.markdown(
            '<div class="memora-logo">M</div>'
            '<h1 class="memora-login-title">IELTS Memora</h1>'
            '<p class="memora-muted">Đăng nhập để lưu tiến độ và điểm số của bạn.</p>',
            unsafe_allow_html=True,
        )
        tab_login, tab_register = st.tabs(["Đăng nhập", "Tạo tài khoản"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Tên đăng nhập", autocomplete="username")
                password = st.text_input("Mật khẩu", type="password", autocomplete="current-password")
                submitted = st.form_submit_button("Đăng nhập", type="primary")
            if submitted:
                ok, msg, user = auth.authenticate(username, password)
                if ok:
                    _sign_in(user)
                    st.rerun()
                else:
                    st.error(msg)

        with tab_register:
            with st.form("register_form"):
                r_user = st.text_input("Tên đăng nhập", help="3–30 ký tự: chữ, số, _ hoặc .", key="reg_user")
                r_name = st.text_input("Tên hiển thị", key="reg_name")
                r_pw = st.text_input("Mật khẩu", type="password", help="Ít nhất 8 ký tự.", key="reg_pw")
                r_pw2 = st.text_input("Nhập lại mật khẩu", type="password", key="reg_pw2")
                created = st.form_submit_button("Tạo tài khoản", type="primary")
            if created:
                ok, msg, uid = auth.register(r_user.strip(), r_name, r_pw, r_pw2)
                if ok:
                    _sign_in({"id": uid, "username": r_user.strip(), "display_name": r_name.strip()})
                    st.rerun()
                else:
                    st.error(msg)
