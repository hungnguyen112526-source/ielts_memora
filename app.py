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

st.set_page_config(page_title="IELTS Memora", page_icon=str(ASSETS / "icon.svg"), layout="wide",
                   initial_sidebar_state="auto")


@st.cache_resource
def _init_db() -> bool:
    db.init_db()
    return True


_init_db()
inject_css()
st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")

user = current_user()


def render_nav(groups: dict, container, current) -> None:
    """Menu tự vẽ (st.navigation chỉ dùng để định tuyến, position="hidden").
    Mục nhiều trang: khối bấm để thu gọn/mở ra, tự mở mục đang xem. Mục chỉ có 1 trang: bấm thẳng."""
    cur = getattr(current, "url_path", None)
    with container:
        for name, group in groups.items():
            if name and len(group) > 1:
                with st.expander(name, icon=SECTION_ICONS.get(name), expanded=any(p.url_path == cur for p in group)):
                    for pg in group:
                        st.page_link(pg, label=pg.title, icon=pg.icon, width="stretch")
            else:
                for pg in group:
                    with st.container(key=f"nav_top_{pg.url_path}"):
                        st.page_link(pg, label=pg.title, icon=pg.icon, width="stretch")


SECTION_ICONS = {"Luyện thi": ":material/school:"}

if user is None:
    login_page = st.Page(login_view, title="Đăng nhập", icon=":material/lock:", url_path="login")
    pg = st.navigation([login_page], position="hidden")
    with st.sidebar:
        sync_cookie()
else:
    is_admin = bool(user.get("is_admin"))
    sections = {
        "": [st.Page("views/home.py", title="Tổng quan", icon=":material/dashboard:", url_path="tongquan", default=True)],
        "Luyện thi": [
            st.Page("views/grammar.py", title="Ngữ pháp", icon=":material/spellcheck:", url_path="nguphap"),
            st.Page("views/reading.py", title="Reading", icon=":material/menu_book:", url_path="reading"),
            st.Page("views/listening.py", title="Listening", icon=":material/headphones:", url_path="listening"),
            st.Page("views/writing.py", title="Writing", icon=":material/edit_note:", url_path="writing"),
            st.Page("views/speaking.py", title="Speaking", icon=":material/mic:", url_path="speaking"),
        ],
        "Tài khoản": [st.Page("views/account.py", title="Tài khoản", icon=":material/person:", url_path="taikhoan")],
    }
    if is_admin:
        sections["Quản trị"] = [st.Page("views/admin.py", title="Quản trị", icon=":material/admin_panel_settings:",
                                         url_path="quantri")]

    with st.sidebar:
        shown = user["display_name"] or user["username"]
        with st.container(key="side_user"):
            st.html(f'<div class="side-id"><div class="side-av">{escape(shown[:1].upper())}</div>'
                    f'<div><div class="side-name">{escape(shown)}</div>'
                    f'<span class="side-role">{"Quản trị" if is_admin else "Học viên"}</span></div></div>')
            if st.button("Đăng xuất", icon=":material/logout:", width="stretch", key="logout_btn"):
                logout()
        nav_slot = st.container(key="side_nav")
        with st.container(key="side_foot"):
            st.caption("Đổi giao diện sáng/tối: menu ⋮ góc trên phải → Settings → Theme.")
        sync_cookie()

    pg = st.navigation(sections, position="hidden")
    render_nav(sections, nav_slot, pg)

pg.run()
