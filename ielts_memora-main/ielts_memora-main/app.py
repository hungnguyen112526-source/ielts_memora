"""IELTS Memora – entry point and router.

Run:  streamlit run app.py
Everything except the login screen is only reachable after signing in,
because pages are registered with st.navigation only for signed-in users."""
from html import escape
from pathlib import Path

import streamlit as st

from core import db
from core.session import current_user, login_view, logout, sync_cookie
from core.ui import inject_css

ASSETS = Path(__file__).resolve().parent / "assets"

st.set_page_config(page_title="IELTS Memora", page_icon=str(ASSETS / "icon.svg"), layout="wide")


@st.cache_resource
def _init_db() -> bool:
    db.init_db()
    return True


_init_db()
inject_css()
st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")

user = current_user()

if user is None:
    login_page = st.Page(login_view, title="Đăng nhập", icon=":material/lock:", url_path="login")
    pg = st.navigation([login_page], position="hidden")
    with st.sidebar:
        sync_cookie()
else:
    pg = st.navigation({
        "": [st.Page("views/home.py", title="Tổng quan", icon=":material/dashboard:", default=True)],
        "Luyện thi": [
            st.Page("views/grammar.py", title="Ngữ pháp", icon=":material/spellcheck:"),
            st.Page("views/reading.py", title="Reading", icon=":material/menu_book:"),
            st.Page("views/listening.py", title="Listening", icon=":material/headphones:"),
            st.Page("views/writing.py", title="Writing", icon=":material/edit_note:"),
            st.Page("views/speaking.py", title="Speaking", icon=":material/mic:"),
        ],
        "Tài khoản": [st.Page("views/account.py", title="Tài khoản", icon=":material/person:")],
    })
    with st.sidebar:
        initial = escape((user["display_name"] or user["username"])[:1].upper())
        st.markdown(
            f'<div class="memora-user"><div class="memora-avatar">{initial}</div>'
            f'<div><b>{escape(user["display_name"])}</b><span>@{escape(user["username"])}</span></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Đăng xuất", icon=":material/logout:", width="stretch"):
            logout()
        sync_cookie()

pg.run()
