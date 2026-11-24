"""IELTS Memora – entry point and router.

Run:  streamlit run app.py
Everything except the login screen is only reachable after signing in,
because pages are registered with st.navigation only for signed-in users."""
import streamlit as st

from core import db
from core.session import current_user, login_view, logout, sync_cookie
from core.ui import inject_css

st.set_page_config(page_title="IELTS Memora", page_icon="🧠", layout="wide")


@st.cache_resource
def _init_db() -> bool:
    db.init_db()
    return True


_init_db()
inject_css()

user = current_user()

if user is None:
    login_page = st.Page(login_view, title="Đăng nhập", icon="🔐", url_path="login")
    pg = st.navigation([login_page])
    with st.sidebar:
        sync_cookie()
else:
    pg = st.navigation({
        "": [st.Page("views/home.py", title="Tổng quan", icon="🏠", default=True)],
        "Luyện thi": [
            st.Page("views/grammar.py", title="Ngữ pháp", icon="📘"),
            st.Page("views/reading.py", title="Reading", icon="📖"),
            st.Page("views/listening.py", title="Listening", icon="🎧"),
            st.Page("views/writing.py", title="Writing", icon="✍️"),
            st.Page("views/speaking.py", title="Speaking", icon="🎤"),
        ],
        "Tài khoản": [st.Page("views/account.py", title="Tài khoản", icon="👤")],
    })
    with st.sidebar:
        st.markdown(f"**{user['display_name']}**")
        st.caption(f"@{user['username']}")
        if st.button("Đăng xuất"):
            logout()
        sync_cookie()

pg.run()
