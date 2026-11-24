"""Shared look & feel. Colours and shapes follow the Orange reader (slate + blue-600, rounded-xl)."""
from __future__ import annotations

import html

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 2rem; max-width: 1100px; }

.memora-logo { width: 44px; height: 44px; border-radius: 12px; background: #2563eb; color: #fff;
  display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 20px; margin: 0 auto 10px; }
.memora-login-title { text-align: center; font-weight: 800; font-size: 1.9rem; margin: 0 0 4px; }
.memora-muted { color: #64748b; font-size: .92rem; }
.memora-center { text-align: center; }

.memora-badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px;
  font-weight: 600; margin-right: 6px; background: #eff6ff; color: #1d4ed8; }
.memora-badge.done { background: #ecfdf5; color: #047857; }
.memora-badge.doing { background: #fffbeb; color: #b45309; }
.memora-badge.todo { background: #f1f5f9; color: #475569; }
.memora-card-title { font-weight: 700; font-size: 1.05rem; margin: 0 0 2px; }
.memora-card-sub { color: #64748b; font-size: .85rem; margin: 0 0 8px; min-height: 2.4em; }
.memora-meta { color: #64748b; font-size: .8rem; margin-bottom: 8px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
.stButton > button { border-radius: 10px; font-weight: 600; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def badge(text: str, kind: str = "") -> str:
    return f'<span class="memora-badge {kind}">{html.escape(text)}</span>'


def page_title(title: str, subtitle: str = "") -> None:
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f'<p class="memora-muted">{html.escape(subtitle)}</p>', unsafe_allow_html=True)


QUESTION_TYPE_LABELS = {
    "tfng": "T/F/NG", "mcq": "Trắc nghiệm", "multi2": "Chọn 2", "matching": "Nối thông tin",
    "notes": "Điền ghi chú", "summary_box": "Tóm tắt (chọn từ)", "summary_text": "Tóm tắt (điền từ)",
    "table": "Bảng", "flowchart": "Sơ đồ",
}


def type_label(t: str) -> str:
    return QUESTION_TYPE_LABELS.get(t, t)


def coming_soon(title: str, subtitle: str, planned: list[str], data_hint: str) -> None:
    page_title(title, subtitle)
    with st.container(border=True):
        st.markdown("**Mục này sẽ có:**")
        for item in planned:
            st.markdown(f"- {item}")
        st.markdown(f"**Khi bạn gửi tài liệu**, nội dung sẽ được đặt trong `{data_hint}`.")
    st.info("Phần này chưa có nội dung. Gửi tài liệu cho mình để bắt đầu.")
