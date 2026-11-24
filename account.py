import streamlit as st

from core import auth
from core.session import current_user
from core.ui import page_title

user = current_user()
page_title("Tài khoản")

with st.container(border=True):
    st.markdown(f"**{user['display_name']}**")
    st.caption(f"Tên đăng nhập: @{user['username']}")

st.markdown("#### Đổi mật khẩu")
with st.form("change_password"):
    old = st.text_input("Mật khẩu hiện tại", type="password")
    new = st.text_input("Mật khẩu mới", type="password", help="Ít nhất 8 ký tự.")
    confirm = st.text_input("Nhập lại mật khẩu mới", type="password")
    go = st.form_submit_button("Đổi mật khẩu", type="primary")

if go:
    ok, msg = auth.change_password(user["id"], old, new, confirm)
    if ok:
        # all sessions were revoked; keep this device signed in with a fresh one
        token = auth.create_session(user["id"])
        st.session_state["_session_token"] = token
        st.session_state["_cookie_token"] = token
        st.success(msg)
    else:
        st.error(msg)
