"""Quản trị: danh sách người dùng, khóa / mở khóa, đặt lại mật khẩu, xóa tài khoản."""
from datetime import datetime
from zoneinfo import ZoneInfo

import os
import json
import sqlite3
import tempfile

import pandas as pd
import streamlit as st

from core import auth, db
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
                st.toast(msg, icon="✅")
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
                st.toast(msg, icon="✅")
                st.rerun()


def _backup_bytes() -> bytes:
    """Bản sao nhất quán của memora.db (dùng cơ chế backup của SQLite, an toàn khi đang có người dùng)."""
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        src, dst = sqlite3.connect(db.DB_PATH), sqlite3.connect(tmp)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp)


section("Lưu trữ và sao lưu")
with st.container(key="card-backup"):
    pg = db.backend() == "postgres"
    if pg:
        st.success("Dữ liệu đang lưu ở PostgreSQL bên ngoài, không bị mất khi app khởi động lại.", icon="✅")
        st.caption("Bạn vẫn có thể tải thêm một bản sao lưu JSON (mật khẩu chỉ ở dạng băm).")
    else:
        st.warning("Đang dùng SQLite (file trên ổ đĩa tạm). Trên Streamlit Cloud, dữ liệu sẽ MẤT khi app khởi động lại. "
                   "Hãy đặt `DATABASE_URL` trong Secrets để lưu bền (xem README, mục Lưu dữ liệu bền).", icon="⚠️")
    # Chỉ dựng bản sao lưu khi bấm nút (trước đây dựng lại ở mỗi lần thao tác trên trang này)
    if st.button("Tạo bản sao lưu", icon=":material/backup:", key="adm_make_backup"):
        st.session_state["_backup"] = (json.dumps(db.export_all(), ensure_ascii=False, indent=1).encode("utf-8") if pg
                                       else _backup_bytes())
    if st.session_state.get("_backup"):
        st.download_button("Tải bản sao lưu", data=st.session_state["_backup"],
                           file_name="memora-backup.json" if pg else "memora-backup.db",
                           mime="application/json" if pg else "application/octet-stream", icon=":material/download:")
