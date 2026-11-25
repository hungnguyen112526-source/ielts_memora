"""Quản trị: danh sách người dùng, khóa / mở khóa, đặt lại mật khẩu, xóa tài khoản."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from core import auth
from core.session import current_user
from core.ui import kpi_row, page_title, section

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
user = current_user()
page_title("Quản trị", "Quản lý tài khoản người học.")

if not user.get("is_admin"):
    st.error("Bạn không có quyền xem trang này.")
    st.stop()


def _fmt(ts):
    return datetime.fromtimestamp(ts, TZ).strftime("%d/%m/%Y %H:%M") if ts else "–"


users = auth.list_users()
kpi_row([
    ("Tài khoản", str(len(users)), None),
    ("Đang bị khóa", str(sum(1 for u in users if u["status"] == "blocked")), None),
    ("Tổng lượt nộp bài", str(sum(u["attempts"] for u in users)), None),
])

section("Danh sách")
with st.container(key="card-users"):
    if users:
        view = pd.DataFrame([{
            "Tên đăng nhập": u["username"], "Tên hiển thị": u["display_name"],
            "Trạng thái": "Đã khóa" if u["status"] == "blocked" else "Hoạt động",
            "Số bài đã nộp": u["attempts"], "Lần nộp gần nhất": _fmt(u["last_attempt"]), "Ngày tạo": _fmt(u["created_at"]),
        } for u in users])
        st.dataframe(view, hide_index=True, width="stretch")
    else:
        st.info("Chưa có tài khoản nào.")

others = [u for u in users if u["username"].lower() != user["username"].lower()]
section("Thao tác")
with st.container(key="card-user-actions"):
    if not others:
        st.info("Chưa có thành viên nào khác.")
    else:
        by_name = {u["username"]: u for u in others}
        target = by_name[st.selectbox("Chọn thành viên", list(by_name))]
        c1, c2, c3 = st.columns(3)
        with c1:
            blocked = target["status"] == "blocked"
            if st.button("Mở khóa" if blocked else "Khóa tài khoản", icon=":material/lock_open:" if blocked else ":material/lock:",
                         width="stretch", key="adm_toggle"):
                ok, msg = auth.set_status(target["id"], "active" if blocked else "blocked")
                st.toast(msg, icon=":material/check_circle:")
                st.rerun()
        with c2:
            new_pw = st.text_input("Mật khẩu mới", type="password", key="adm_pw", label_visibility="collapsed",
                                   placeholder="Mật khẩu mới (từ 8 ký tự)")
            if st.button("Đặt lại mật khẩu", icon=":material/key:", width="stretch", key="adm_reset"):
                ok, msg = auth.admin_reset_password(target["id"], new_pw)
                (st.success if ok else st.error)(msg)
        with c3:
            confirm = st.checkbox(f"Xác nhận xóa '{target['username']}'", key="adm_confirm")
            if st.button("Xóa tài khoản", icon=":material/delete:", width="stretch", disabled=not confirm, key="adm_delete"):
                ok, msg = auth.delete_user(target["id"])
                st.toast(msg, icon=":material/check_circle:")
                st.rerun()
