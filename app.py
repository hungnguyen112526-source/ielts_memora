"""IELTS Memora – entry point and router.

Run:  streamlit run app.py
Everything except the login screen is only reachable after signing in,
because pages are registered with st.navigation only for signed-in users."""
from html import escape
from pathlib import Path

import streamlit as st

from core import catalog as cat_mod
from core import db
from core.reading_nav import close_test, current_category
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


READING_PAGE = "views/reading.py"


def reading_nav(cur) -> None:
    """Mục Reading ở sidebar: bấm để mở/đóng danh sách 4 mục con (Band 4–5.0, Band 5–6.5, Orange, Vol)."""
    catalog = cat_mod.load_catalog()
    on_reading = cur == "reading"
    flag = st.session_state.get("nav_reading_open")
    is_open = on_reading if flag is None else bool(flag)
    active = current_category(catalog)["id"] if on_reading else None
    with st.container(key="nav_reading"):
        with st.container(key=f"nav_reading_btn_{'open' if is_open else 'shut'}"):
            if st.button("Reading", icon=":material/menu_book:", key="nav_reading_toggle", type="tertiary", width="stretch"):
                if on_reading:
                    st.session_state["nav_reading_open"] = not is_open
                    st.rerun()
                st.session_state["nav_reading_open"] = True
                st.switch_page(READING_PAGE)
        if is_open:
            with st.container(key="nav_reading_sub"):
                for c in catalog["categories"]:
                    state = "active" if c["id"] == active else "idle"
                    with st.container(key=f"navsub-{c['id']}-{state}"):
                        if st.button(c["title"], key=f"nav_cat_{c['id']}", type="tertiary", width="stretch"):
                            st.session_state["reading_cat"] = c["id"]
                            st.session_state["nav_reading_open"] = True
                            close_test()
                            st.switch_page(READING_PAGE)


def render_nav(pages: list, container, current) -> None:
    """Menu tự vẽ (st.navigation chỉ dùng để định tuyến, position="hidden").
    Danh sách phẳng; riêng Reading có menu thả xuống cho các mục con."""
    cur = getattr(current, "url_path", None)
    with container:
        for pg in pages:
            if pg.url_path == "reading":
                reading_nav(cur)
            else:
                with st.container(key=f"nav_top_{pg.url_path}"):
                    st.page_link(pg, label=pg.title, icon=pg.icon, width="stretch")


if user is None:
    login_page = st.Page(login_view, title="Đăng nhập", icon=":material/lock:", url_path="login")
    pg = st.navigation([login_page], position="hidden")
    with st.sidebar:
        sync_cookie()
else:
    is_admin = bool(user.get("is_admin"))
    pages = [
        st.Page("views/home.py", title="Tổng quan", icon=":material/dashboard:", url_path="tongquan", default=True),
        st.Page("views/grammar.py", title="Ngữ pháp", icon=":material/spellcheck:", url_path="nguphap"),
        st.Page("views/reading.py", title="Reading", icon=":material/menu_book:", url_path="reading"),
        st.Page("views/listening.py", title="Listening", icon=":material/headphones:", url_path="listening"),
        st.Page("views/writing.py", title="Writing", icon=":material/edit_note:", url_path="writing"),
        st.Page("views/speaking.py", title="Speaking", icon=":material/mic:", url_path="speaking"),
        st.Page("views/account.py", title="Tài khoản", icon=":material/person:", url_path="taikhoan"),
    ]
    if is_admin:
        pages.append(st.Page("views/admin.py", title="Quản trị", icon=":material/admin_panel_settings:",
                             url_path="quantri"))

    with st.sidebar:
        nav_slot = st.container(key="side_nav")
        with st.container(key="side_foot"):
            st.caption("Đổi giao diện sáng/tối: menu ⋮ góc trên phải → Settings → Theme.")
        shown = user["display_name"] or user["username"]
        with st.container(key="side_user"):                 # khối tài khoản nằm cuối sidebar (CSS đẩy xuống đáy)
            st.html(f'<div class="side-id"><div class="side-av">{escape(shown[:1].upper())}</div>'
                    f'<div><div class="side-name">{escape(shown)}</div>'
                    f'<span class="side-role">{"Quản trị" if is_admin else "Học viên"}</span></div></div>')
            if st.button("Đăng xuất", icon=":material/logout:", width="stretch", key="logout_btn"):
                logout()
        sync_cookie()

    pg = st.navigation(pages, position="hidden")
    render_nav(pages, nav_slot, pg)

pg.run()
