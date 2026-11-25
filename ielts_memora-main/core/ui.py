"""Giao diện dùng chung. Ngôn ngữ thiết kế lấy từ cam21: nền slate-50, thẻ trắng bo góc,
màu chính blue-600, Inter đậm cho tiêu đề, badge trạng thái xanh / vàng / xám."""
from __future__ import annotations

import html

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ---------- nền tảng ---------- */
html, body, .stApp, [class*="st-"], button, input, textarea { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: #f8fafc; color: #0f172a; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stDeployButton { display: none !important; visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; height: 2.5rem; }
.block-container, [data-testid="stMainBlockContainer"] { max-width: 1120px; padding: 2.75rem 2rem 4rem; }
::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 9999px; }
:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e2e8f0; }
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { padding: 1.25rem 1rem .5rem; }
[data-testid="stSidebarNav"] { padding-top: .25rem; }
[data-testid="stSidebarNavLink"] { border-radius: 12px; margin: 1px 8px; padding: .5rem .75rem;
  font-weight: 600; color: #475569; transition: background .15s, color .15s; }
[data-testid="stSidebarNavLink"]:hover { background: #f1f5f9; color: #0f172a; }
[data-testid="stSidebarNavLink"][aria-current="page"] { background: #eff6ff; color: #1d4ed8; }
[data-testid="stSidebarNavLink"][aria-current="page"] span { color: #1d4ed8; }
[data-testid="stSidebarNavSeparator"] { display: none; }
[data-testid="stNavSectionHeader"], [data-testid="stSidebarNav"] header { color: #94a3b8; font-weight: 700;
  font-size: .78rem; padding-left: 1.1rem; }

.memora-user { display: flex; align-items: center; gap: 10px; padding: 12px; border: 1px solid #e2e8f0;
  border-radius: 14px; background: #f8fafc; margin: 8px 0 10px; }
.memora-avatar { width: 38px; height: 38px; border-radius: 12px; background: #dbeafe; color: #1d4ed8;
  display: flex; align-items: center; justify-content: center; font-weight: 800; flex-shrink: 0; }
.memora-user b { display: block; font-size: .9rem; line-height: 1.2; color: #0f172a; }
.memora-user span { font-size: .78rem; color: #64748b; }

/* ---------- chữ ---------- */
.memora-title { font-size: 1.85rem; font-weight: 800; letter-spacing: -.02em; color: #0f172a; margin: 0 0 4px; line-height: 1.2; }
.memora-subtitle, .memora-muted { color: #64748b; font-size: .95rem; margin: 0 0 1.25rem; }
.memora-section { font-size: 1.05rem; font-weight: 800; color: #0f172a; margin: 1.75rem 0 .75rem; }
.memora-section small { font-weight: 600; color: #64748b; margin-left: 8px; font-size: .8rem; }

/* ---------- thẻ ---------- */
[class*="st-key-card-"], .memora-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 16px;
  padding: 20px 22px; box-shadow: 0 1px 2px rgba(15, 23, 42, .04); transition: border-color .15s, box-shadow .15s; }
[class*="st-key-card-test-"]:hover { border-color: #93c5fd; box-shadow: 0 6px 18px rgba(37, 99, 235, .08); }
.memora-card-title { font-weight: 800; font-size: 1.1rem; color: #0f172a; margin: 0; }
.memora-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.memora-plist { list-style: none; padding: 0; margin: 0 0 6px; }
.memora-plist li { display: flex; gap: 8px; font-size: .86rem; color: #475569; padding: 2px 0; }
.memora-plist li b { color: #2563eb; flex-shrink: 0; }
.memora-plist li span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.memora-meta { color: #64748b; font-size: .8rem; font-weight: 500; margin: 0; padding-top: 6px; }

.memora-stat { background: #fff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 18px 20px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, .04); }
.memora-stat .label { color: #64748b; font-size: .82rem; font-weight: 600; }
.memora-stat .value { font-size: 2rem; font-weight: 800; letter-spacing: -.02em; color: #0f172a; line-height: 1.15; margin-top: 4px; }
.memora-stat .hint { color: #94a3b8; font-size: .78rem; margin-top: 2px; }
.memora-stat.accent .value { color: #2563eb; }

.memora-badge { display: inline-block; padding: 3px 10px; border-radius: 8px; font-size: .75rem; font-weight: 700;
  background: #eff6ff; color: #1d4ed8; white-space: nowrap; }
.memora-badge.done { background: #d1fae5; color: #047857; }
.memora-badge.doing { background: #fef3c7; color: #b45309; }
.memora-badge.todo { background: #f1f5f9; color: #475569; }

.memora-bar { height: 8px; border-radius: 9999px; background: #e2e8f0; overflow: hidden; margin: 8px 0 2px; }
.memora-bar i { display: block; height: 100%; background: #2563eb; border-radius: 9999px; }

.memora-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.memora-table th { text-align: left; color: #64748b; font-weight: 600; font-size: .78rem; padding: 0 8px 8px; border-bottom: 1px solid #e2e8f0; }
.memora-table td { padding: 10px 8px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.memora-table tr:last-child td { border-bottom: 0; }
.memora-table td.num { font-variant-numeric: tabular-nums; }
.memora-table td.name { font-weight: 600; color: #0f172a; }

.memora-empty { text-align: center; padding: 18px 8px 4px; }
.memora-empty b { display: block; font-size: 1.05rem; color: #0f172a; margin-bottom: 4px; }
.memora-empty p { color: #64748b; margin: 0 0 12px; font-size: .92rem; }

.memora-soon-list { list-style: none; padding: 0; margin: 14px 0 0; }
.memora-soon-list li { position: relative; padding: 8px 0 8px 28px; color: #334155; font-size: .95rem; border-top: 1px solid #f1f5f9; }
.memora-soon-list li::before { content: ""; position: absolute; left: 4px; top: 13px; width: 12px; height: 12px;
  border-radius: 50%; border: 2px solid #93c5fd; }

/* ---------- nút, ô nhập, tab ---------- */
.stButton > button, .stFormSubmitButton > button { border-radius: 12px; font-weight: 700; border: 1px solid #cbd5e1;
  padding: .45rem 1rem; transition: background .15s, border-color .15s; }
.stButton > button:hover, .stFormSubmitButton > button:hover { border-color: #93c5fd; color: #1d4ed8; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background: #2563eb; border-color: #2563eb; color: #fff;
  box-shadow: 0 1px 2px rgba(37, 99, 235, .3); }
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover { background: #1d4ed8; border-color: #1d4ed8; color: #fff; }
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="base-input"] { border-radius: 12px !important; }
[data-baseweb="input"], [data-baseweb="base-input"] { background: #fff !important; }
div[data-baseweb="input"] { border: 1px solid #cbd5e1 !important; }
div[data-baseweb="input"]:focus-within { border-color: #2563eb !important; box-shadow: 0 0 0 3px rgba(37, 99, 235, .15); }
input:-webkit-autofill { -webkit-box-shadow: 0 0 0 40px #fff inset !important; -webkit-text-fill-color: #0f172a !important; }
[data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid #e2e8f0; }
button[data-baseweb="tab"] { font-weight: 700; color: #64748b; padding: .5rem .9rem; }
button[data-baseweb="tab"][aria-selected="true"] { color: #1d4ed8; }
[data-baseweb="tab-highlight"] { background: #2563eb; height: 3px; border-radius: 3px; }
[data-testid="stForm"] { border: 0; padding: 0; }

@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding: 2.5rem 1rem 3rem; }
  .memora-title { font-size: 1.5rem; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(x) -> str:
    return html.escape(str(x))


def badge(text: str, kind: str = "") -> str:
    return f'<span class="memora-badge {kind}">{esc(text)}</span>'


def page_title(title: str, subtitle: str = "") -> None:
    st.markdown(f'<h1 class="memora-title">{esc(title)}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="memora-subtitle">{esc(subtitle)}</p>', unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    small = f"<small>{esc(note)}</small>" if note else ""
    st.markdown(f'<div class="memora-section">{esc(title)}{small}</div>', unsafe_allow_html=True)


def stat_card(label: str, value, hint: str = "", accent: bool = False) -> str:
    cls = "memora-stat accent" if accent else "memora-stat"
    hint_html = f'<div class="hint">{esc(hint)}</div>' if hint else ""
    return (f'<div class="{cls}"><div class="label">{esc(label)}</div>'
            f'<div class="value">{esc(value)}</div>{hint_html}</div>')


def progress_bar(done: int, total: int) -> str:
    pct = 0 if total <= 0 else max(0, min(100, round(done * 100 / total)))
    return f'<div class="memora-bar"><i style="width:{pct}%"></i></div>'


QUESTION_TYPE_LABELS = {
    "tfng": "T/F/NG", "mcq": "Trắc nghiệm", "multi2": "Chọn 2", "matching": "Nối thông tin",
    "notes": "Điền ghi chú", "summary_box": "Tóm tắt (chọn từ)", "summary_text": "Tóm tắt (điền từ)",
    "table": "Bảng", "flowchart": "Sơ đồ",
}


def type_label(t: str) -> str:
    return QUESTION_TYPE_LABELS.get(t, t)


def coming_soon(title: str, subtitle: str, planned: list[str], data_hint: str = "") -> None:
    """Trang giữ chỗ. `data_hint` chỉ dành cho người làm nội dung nên không hiện ra cho người học."""
    page_title(title, subtitle)
    items = "".join(f"<li>{esc(i)}</li>" for i in planned)
    with st.container(key="card-soon"):
        st.markdown(f'{badge("Sắp có", "doing")}<ul class="memora-soon-list">{items}</ul>',
                    unsafe_allow_html=True)
