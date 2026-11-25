import streamlit as st

from core import auth
from core.session import current_user
from core.ui import esc, page_title, section

user = current_user()
page_title("Tài khoản", "Thông tin đăng nhập và bảo mật.")

with st.container(key="card-profile"):
    initial = esc((user["display_name"] or user["username"])[:1].upper())
    st.markdown(
        f'<div class="memora-user" style="margin:0;border:0;background:none;padding:0">'
        f'<div class="memora-avatar" style="width:52px;height:52px;font-size:1.3rem">{initial}</div>'
        f'<div><b style="font-size:1.05rem">{esc(user["display_name"])}</b>'
        f'<span>Tên đăng nhập: @{esc(user["username"])}</span></div></div>',
        unsafe_allow_html=True,
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
            st.success(msg)
        else:
            st.error(msg)
