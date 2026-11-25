"""Streamlit-side login state: who is signed in, login/register forms, persistent cookie."""
from __future__ import annotations

import os

import streamlit as st

from . import auth
from .reader_component import cookie_bridge

COOKIE_NAME = "memora_session"


def _read_cookie() -> str | None:
    try:
        value = st.context.cookies.get(COOKIE_NAME)
        return value if isinstance(value, str) else None
    except Exception:          # old Streamlit without st.context, or no request context
        return None


def _admin_names() -> list[str]:
    """Danh sách quản trị: Secrets `ADMIN_USERNAMES` (Streamlit Cloud) hoặc biến môi trường MEMORA_ADMINS (cách nhau bằng dấu phẩy)."""
    names: list[str] = [n for n in os.environ.get("MEMORA_ADMINS", "").split(",") if n.strip()]
    try:
        raw = st.secrets.get("ADMIN_USERNAMES", [])
        names += [raw] if isinstance(raw, str) else list(raw)
    except Exception:       # chưa có file secrets
        pass
    return names


def current_user() -> dict | None:
    user = _current_user()
    if user is not None:
        user["is_admin"] = auth.is_admin(user["username"], _admin_names())
    return user


def _current_user() -> dict | None:
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


LOGIN_CSS = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"] { display: none !important; }
[data-testid="stAppViewContainer"] { background:
  radial-gradient(700px 420px at 12% -5%, color-mix(in srgb, var(--m-accent) 16%, transparent), transparent 70%),
  radial-gradient(600px 400px at 100% 105%, color-mix(in srgb, var(--m-accent) 11%, transparent), transparent 70%); }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 7vh; max-width: 480px; }
.memora-hero { text-align: center; margin-bottom: 1.3rem; }
.memora-hero .mark { width: 64px; height: 64px; border-radius: 20px; margin: 0 auto 14px; display: block;
  box-shadow: 0 12px 26px -8px color-mix(in srgb, var(--m-accent) 70%, transparent); }
.memora-hero h1 { font-size: 2rem; font-weight: 800; letter-spacing: -.035em; margin: 0 0 6px; }
.memora-hero p { opacity: .7; margin: 0; font-size: .96rem; }
.st-key-card-login { padding: 26px 30px 24px; border-radius: 28px; backdrop-filter: blur(6px);
  box-shadow: 0 40px 80px -48px color-mix(in srgb, var(--m-accent) 55%, transparent), var(--m-shadow); }
.st-key-card-login [data-baseweb="tab-list"] { gap: 0; margin-bottom: 1.1rem; }
.st-key-card-login button[data-baseweb="tab"] { flex: 1 1 0; justify-content: center; padding: .65rem .5rem; }
.st-key-card-login [data-testid="stTextInput"] { margin-bottom: .15rem; }
.st-key-card-login [data-testid="stFormSubmitButton"], .st-key-card-login [data-testid="stFormSubmitButton"] button { width: 100%; }
.st-key-card-login [data-testid="stFormSubmitButton"] button { min-height: 46px; font-size: 1rem; margin-top: .3rem; }
.st-key-card-login [data-testid="stAlert"] { border-radius: 14px; }
.memora-hint { text-align: center; border: 0; background: color-mix(in srgb, currentColor 5%, transparent); border-radius: 14px;
  padding: .65rem .9rem; font-size: .85rem; opacity: .85; margin-top: 1rem; }
.memora-perks { display: flex; justify-content: center; flex-wrap: wrap; gap: 6px 16px; margin-top: 1.3rem; opacity: .7; font-size: .82rem; font-weight: 600; }
.memora-perks span::before { content: ""; display: inline-block; width: 6px; height: 6px; border-radius: 50%;
  background: var(--m-accent); margin-right: 7px; vertical-align: middle; }
@media (max-width: 640px) { .block-container, [data-testid="stMainBlockContainer"] { padding-top: 3.6rem; } }
</style>
"""

MARK_SVG = ("data:image/svg+xml;utf8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' "
            "height='64' rx='16' fill='%232563eb'/%3E%3Cpath d='M17 46V18h6.5l8.5 14 8.5-14H47v28h-6.2V28.6l-7.3 12h-3l-7.3-12V46z' "
            "fill='%23fff'/%3E%3C/svg%3E")


def login_view() -> None:
    """Login / register screen (shown by app.py whenever nobody is signed in)."""
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)
    with st.container():
        st.markdown(
            f'<div class="memora-hero"><img class="mark" src="{MARK_SVG}" alt="">'
            '<h1>IELTS Memora</h1>'
            '<p>Đăng nhập để lưu tiến độ và điểm số của bạn.</p></div>',
            unsafe_allow_html=True,
        )
        with st.container(key="card-login"):
            tab_login, tab_register = st.tabs([":material/login: Đăng nhập", ":material/person_add: Tạo tài khoản"])

            with tab_login:
                with st.form("login_form"):
                    username = st.text_input("Tên đăng nhập", autocomplete="username")
                    password = st.text_input("Mật khẩu", type="password", autocomplete="current-password")
                    submitted = st.form_submit_button("Đăng nhập", type="primary", width="stretch")
                if submitted:
                    ok, msg, user = auth.authenticate(username, password)
                    if ok:
                        _sign_in(user)
                        st.rerun()
                    else:
                        st.error(msg)
                st.markdown('<div class="memora-hint">Chưa có tài khoản? Chuyển sang tab <b>Tạo tài khoản</b>, '
                            'miễn phí và dùng được ngay.</div>', unsafe_allow_html=True)

            with tab_register:
                with st.form("register_form"):
                    r_user = st.text_input("Tên đăng nhập", help="3–30 ký tự: chữ, số, _ hoặc .", key="reg_user")
                    r_name = st.text_input("Tên hiển thị", key="reg_name")
                    r_pw = st.text_input("Mật khẩu", type="password", help="Ít nhất 8 ký tự.", key="reg_pw")
                    r_pw2 = st.text_input("Nhập lại mật khẩu", type="password", key="reg_pw2")
                    created = st.form_submit_button("Tạo tài khoản", type="primary", width="stretch")
                if created:
                    ok, msg, uid = auth.register(r_user.strip(), r_name, r_pw, r_pw2)
                    if ok:
                        _sign_in({"id": uid, "username": r_user.strip(), "display_name": r_name.strip()})
                        st.rerun()
                    else:
                        st.error(msg)

        st.markdown(
            '<div class="memora-perks"><span>Giao diện thi máy</span><span>Chấm band tự động</span>'
            '<span>Lưu tiến độ theo tài khoản</span></div>',
            unsafe_allow_html=True,
        )
