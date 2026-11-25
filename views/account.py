import streamlit as st

from core import auth
from core.session import current_user
from core.ui import badge, esc, page_title, section

user = current_user()
page_title("Tài khoản", "Thông tin đăng nhập và bảo mật.")

with st.container(key="card-profile"):
    initial = esc((user["display_name"] or user["username"])[:1].upper())
    role = badge("Quản trị", "") if user.get("is_admin") else badge("Học viên", "")
    st.html(
        f'<div class="side-id" style="margin:0"><div class="side-av" style="width:3.2rem;height:3.2rem;font-size:1.3rem">{initial}</div>'
        f'<div><div class="side-name" style="font-size:1.1rem">{esc(user["display_name"])}</div>'
        f'<span class="memora-meta" style="padding:0">Tên đăng nhập: @{esc(user["username"])}</span><br>{role}</div></div>'
    )

section("Đổi mật khẩu")
with st.container(key="card-password"):
    with st.form("change_password"):
        old = st.text_input("Mật khẩu hiện tại", type="password")
        new = st.text_input("Mật khẩu mới", type="password", help="Ít nhất 8 ký tự.")
        confirm = st.text_input("Nhập lại mật khẩu mới", type="password")
        go = st.form_submit_button("Đổi mật khẩu", type="primary")

    if go:
        ok, msg = auth.change_password(user["id"], old, new, confirm)
        if ok:
            # mọi phiên cũ đã bị hủy; giữ thiết bị này đăng nhập bằng một phiên mới
            token = auth.create_session(user["id"])
            st.session_state["_session_token"] = token
            st.session_state["_cookie_token"] = token
            st.toast(msg, icon=":material/check_circle:")
            st.success(msg)
        else:
            st.error(msg)
