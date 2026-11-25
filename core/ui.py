"""Giao diện dùng chung (bố cục và cách tương tác theo dự án rs-dashboard, màu giữ nguyên xanh blue-600).

Màu lấy từ biến CSS --m-* và đổi theo theme sáng/tối của Streamlit (st.context.theme)."""
from __future__ import annotations

import html

import streamlit as st

LIGHT = {
    "card": "#ffffff", "line": "#e2e8f0", "text": "#0f172a", "muted": "#64748b", "soft": "#f1f5f9",
    "accent": "#2563eb", "accent2": "#38bdf8", "accent-soft": "#eff6ff", "accent-text": "#1d4ed8",
    "done-bg": "#d1fae5", "done-text": "#047857", "doing-bg": "#fef3c7", "doing-text": "#b45309",
    "shadow": "0 30px 60px -42px rgba(30, 41, 90, .35)", "side": "#ffffff",
}
DARK = {
    "card": "#111a2e", "line": "#23304a", "text": "#e2e8f0", "muted": "#94a3b8", "soft": "#18233d",
    "accent": "#3b82f6", "accent2": "#38bdf8", "accent-soft": "rgba(59,130,246,.16)", "accent-text": "#93c5fd",
    "done-bg": "rgba(16,185,129,.18)", "done-text": "#6ee7b7", "doing-bg": "rgba(245,158,11,.18)", "doing-text": "#fcd34d",
    "shadow": "0 30px 60px -42px rgba(0, 0, 0, .7)", "side": "#0e1627",
}

CSS = """
<style>
/* ---------- nền tảng ---------- */
.stApp, .stApp *:not([data-testid="stIconMaterial"]):not([class*="material-symbols"]):not(code):not(pre):not(kbd) {
  font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif; }
[data-testid="stIconMaterial"], [class*="material-symbols"] { font-family: 'Material Symbols Rounded' !important; }
footer, .stDeployButton, [data-testid="stDeployButton"] { display: none !important; }
.block-container, [data-testid="stMainBlockContainer"] { max-width: 1200px; padding: 4.5rem 2rem 4rem; }
h1, h2, h3 { font-weight: 800 !important; letter-spacing: -.03em !important; }
::-webkit-scrollbar { width: 7px; height: 7px; }
::-webkit-scrollbar-thumb { background: color-mix(in srgb, currentColor 25%, transparent); border-radius: 9999px; }
:focus-visible { outline: 2px solid var(--m-accent); outline-offset: 2px; }

/* ---------- thẻ ---------- */
[class*="st-key-card-"], .memora-card { background: var(--m-card); border: 1px solid var(--m-line); border-radius: 24px;
  padding: 20px 24px; box-shadow: var(--m-shadow); }
[class*="st-key-card-test-"], [class*="st-key-card-feat-"] { transition: border-color .15s ease, transform .15s ease; }
[class*="st-key-card-test-"]:hover, [class*="st-key-card-feat-"]:hover { border-color: color-mix(in srgb, var(--m-accent) 55%, transparent); transform: translateY(-2px); }
[data-testid="stMetricValue"] { font-weight: 800; letter-spacing: -.03em; }
[data-testid="stMetricLabel"] p { opacity: .7; font-size: .85rem; font-weight: 700; }
[data-testid="stExpander"] details { border-radius: 18px; }
[data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; }

/* ---------- nút: chính (xanh) / phụ (viền) / nhẹ (rê chuột mới hiện nền) ---------- */
[data-testid^="stBaseButton-"] { border-radius: 999px !important; font-weight: 700; letter-spacing: -.01em; min-height: 40px;
  padding: .25rem 1.1rem; transition: background-color .15s ease, border-color .15s ease, box-shadow .15s ease, transform .15s ease; }
[data-testid^="stBaseButton-"]:active { transform: scale(.98); }
[data-testid^="stBaseButton-"]:disabled { opacity: .45; cursor: not-allowed; box-shadow: none !important; }
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {
  background: transparent; border: 1px solid color-mix(in srgb, currentColor 20%, transparent); }
[data-testid="stBaseButton-secondary"]:hover:not(:disabled), [data-testid="stBaseButton-secondaryFormSubmit"]:hover:not(:disabled) {
  background: var(--m-accent-soft); border-color: color-mix(in srgb, var(--m-accent) 60%, transparent); color: inherit; }
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, var(--m-accent), #3b82f6) !important; color: #fff !important; border: 0 !important;
  box-shadow: 0 10px 22px -10px color-mix(in srgb, var(--m-accent) 85%, transparent); }
[data-testid="stBaseButton-primary"]:hover:not(:disabled), [data-testid="stBaseButton-primaryFormSubmit"]:hover:not(:disabled) {
  filter: brightness(1.08); transform: translateY(-1px); }
[data-testid="stBaseButton-tertiary"] { background: transparent; border: 0; min-height: 36px; padding: .2rem .6rem; }
[data-testid="stBaseButton-tertiary"]:hover:not(:disabled) { background: color-mix(in srgb, currentColor 9%, transparent); color: inherit; }

/* ---------- nút chọn (segmented control): một thanh liền, ô đang chọn tô xanh ---------- */
[data-testid="stButtonGroup"] [role="radiogroup"], [data-testid="stButtonGroup"] [role="group"] {
  display: inline-flex; flex-wrap: nowrap; gap: 2px !important; padding: 3px; border-radius: 999px;
  background: color-mix(in srgb, currentColor 7%, transparent); border: 1px solid color-mix(in srgb, currentColor 8%, transparent); }
[data-testid="stButtonGroup"] button[data-variant="segmented_control"] { border: 0 !important; background: transparent !important;
  box-shadow: none !important; border-radius: 999px !important; min-height: 32px !important; padding: 0 .95rem !important;
  font-weight: 700; color: inherit !important; }
[data-testid="stButtonGroup"] button[data-variant="segmented_control"]:hover:not([data-selected="true"]) { background: color-mix(in srgb, currentColor 10%, transparent) !important; }
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][data-selected="true"],
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][aria-checked="true"] {
  background: linear-gradient(135deg, var(--m-accent), #3b82f6) !important; color: #fff !important;
  box-shadow: 0 6px 14px -6px color-mix(in srgb, var(--m-accent) 90%, transparent) !important; }
[data-testid="stButtonGroup"] button[data-variant="segmented_control"] p { color: inherit !important; }

/* ---------- ô nhập, tab ---------- */
[data-testid="stTextInput"] [data-baseweb="input"] { border-radius: 999px; }
[data-testid="stTextInput"] [data-baseweb="input"]:focus-within { border-color: var(--m-accent) !important; box-shadow: 0 0 0 3px color-mix(in srgb, var(--m-accent) 20%, transparent); }
[data-testid="stSelectbox"] [data-baseweb="select"] > div { border-radius: 16px; }
[data-testid="stForm"] { border: 0; padding: 0; }
input:-webkit-autofill { -webkit-box-shadow: 0 0 0 40px var(--m-card) inset !important; -webkit-text-fill-color: var(--m-text) !important; }
button[data-baseweb="tab"] { font-weight: 700; }
[data-baseweb="tab-highlight"] { background: var(--m-accent); height: 3px; border-radius: 3px; }

/* ---------- thanh bên: người dùng, menu thu gọn, chân ---------- */
[data-testid="stSidebar"] { border-right: 1px solid var(--m-line); }
.st-key-side_user { border: 1px solid var(--m-line); border-radius: 18px; padding: .7rem .75rem .6rem; background: color-mix(in srgb, currentColor 4%, transparent); }
.side-id { display: flex; align-items: center; gap: .65rem; margin-bottom: .55rem; }
.side-av { flex: 0 0 auto; width: 2.35rem; height: 2.35rem; border-radius: 50%; display: grid; place-items: center; color: #fff; font-weight: 800;
  background: linear-gradient(135deg, var(--m-accent), var(--m-accent2)); }
.side-name { font-weight: 800; letter-spacing: -.02em; line-height: 1.2; overflow-wrap: anywhere; }
.side-role { display: inline-block; margin-top: .15rem; padding: .05rem .5rem; border-radius: 999px; font-size: .72rem; font-weight: 800; background: var(--m-accent-soft); color: var(--m-accent-text); }
.st-key-side_nav { gap: 4px !important; margin: .6rem 0 .4rem; }
.st-key-side_nav [data-testid="stElementContainer"] { margin: 0; }
.st-key-side_nav [data-testid="stPageLink-NavLink"] { position: relative; border-radius: 14px; font-weight: 600; padding: .38rem .8rem; min-height: 40px;
  transition: background-color .15s ease, transform .15s ease; }
.st-key-side_nav [data-testid="stPageLink-NavLink"]:hover:not([aria-current="page"]) { background: color-mix(in srgb, currentColor 7%, transparent); transform: translateX(2px); }
.st-key-side_nav [data-testid="stPageLink-NavLink"][aria-current="page"] { background: var(--m-accent-soft); color: var(--m-accent-text); font-weight: 800; }
.st-key-side_nav [data-testid="stPageLink-NavLink"][aria-current="page"]::before { content: ""; position: absolute; left: 0; top: 22%; bottom: 22%;
  width: 4px; border-radius: 0 4px 4px 0; background: linear-gradient(180deg, var(--m-accent), var(--m-accent2)); }
.st-key-side_nav [class*="st-key-nav_top_"] [data-testid="stPageLink-NavLink"] { font-weight: 800; }
.st-key-side_nav [data-testid="stExpander"] details { border: 0 !important; background: transparent !important; }
.st-key-side_nav [data-testid="stExpander"] summary { padding: .45rem .8rem; min-height: 40px; border-radius: 14px; font-weight: 800; }
.st-key-side_nav [data-testid="stExpander"] summary:hover { background: color-mix(in srgb, currentColor 7%, transparent); }
.st-key-side_nav [data-testid="stExpanderDetails"] { gap: 2px; padding: 0 0 .25rem .35rem; margin-left: 1.2rem; border-left: 2px solid color-mix(in srgb, currentColor 13%, transparent); }
.st-key-side_nav [data-testid="stExpanderDetails"] [data-testid="stPageLink-NavLink"] { font-weight: 600; font-size: .93rem; min-height: 36px; }
.st-key-side_foot { margin-top: .4rem; }
.st-key-side_foot [data-testid="stCaptionContainer"] { opacity: .6; font-size: .78rem; }

/* ---------- chữ, badge, bảng ---------- */
.memora-title { font-size: 1.9rem; font-weight: 800; letter-spacing: -.035em; margin: 0 0 4px; line-height: 1.15; }
.memora-subtitle, .memora-muted { opacity: .72; font-size: .95rem; margin: 0 0 1.25rem; }
.memora-section { font-size: 1.1rem; font-weight: 800; letter-spacing: -.02em; margin: 1.9rem 0 .75rem; }
.memora-card-title { font-weight: 800; font-size: 1.08rem; letter-spacing: -.02em; margin: 0; }
.memora-card-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }
.memora-plist { list-style: none; padding: 0; margin: 0 0 6px; }
.memora-plist li { display: flex; gap: 8px; font-size: .86rem; padding: 2px 0; opacity: .85; }
.memora-plist li b { color: var(--m-accent-text); flex-shrink: 0; }
.memora-plist li span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.memora-meta { opacity: .65; font-size: .8rem; font-weight: 500; margin: 0; padding-top: 6px; }
.memora-badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: .75rem; font-weight: 700; white-space: nowrap;
  background: var(--m-accent-soft); color: var(--m-accent-text); }
.memora-badge.done { background: var(--m-done-bg); color: var(--m-done-text); }
.memora-badge.doing { background: var(--m-doing-bg); color: var(--m-doing-text); }
.memora-badge.todo { background: color-mix(in srgb, currentColor 10%, transparent); color: inherit; opacity: .8; }
.memora-bar { height: 8px; border-radius: 9999px; background: color-mix(in srgb, currentColor 13%, transparent); overflow: hidden; margin: 8px 0 2px; }
.memora-bar i { display: block; height: 100%; background: linear-gradient(90deg, var(--m-accent), var(--m-accent2)); border-radius: 9999px; }
.memora-series { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin: 1.6rem 0 .25rem; }
.memora-series h3 { font-size: 1.15rem; margin: 0; padding: 0; }
.memora-series span { font-size: .8rem; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--m-accent-soft); color: var(--m-accent-text); }
.memora-series-desc { opacity: .7; font-size: .88rem; margin: 0 0 .75rem; }
.memora-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.memora-table th { text-align: left; opacity: .65; font-weight: 700; font-size: .78rem; padding: 0 8px 8px; border-bottom: 1px solid var(--m-line); }
.memora-table td { padding: 10px 8px; border-bottom: 1px solid color-mix(in srgb, currentColor 7%, transparent); }
.memora-table tr:last-child td { border-bottom: 0; }
.memora-table td.num { font-variant-numeric: tabular-nums; }
.memora-table td.name { font-weight: 700; }
.memora-empty { text-align: center; padding: 14px 8px 4px; }
.memora-empty b { display: block; font-size: 1.05rem; margin-bottom: 4px; }
.memora-empty p { opacity: .7; margin: 0 0 12px; font-size: .92rem; }
.memora-soon-list { list-style: none; padding: 0; margin: 14px 0 0; }
.memora-soon-list li { position: relative; padding: 9px 0 9px 28px; font-size: .95rem; border-top: 1px solid color-mix(in srgb, currentColor 8%, transparent); }
.memora-soon-list li::before { content: ""; position: absolute; left: 4px; top: 14px; width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--m-accent); }
.memora-hint { border: 1px dashed color-mix(in srgb, currentColor 25%, transparent); border-radius: 14px; padding: .7rem .9rem; font-size: .85rem; opacity: .85; margin-top: .6rem; }

/* ---------- trang chủ ---------- */
.home-kicker { font-weight: 700; font-size: .95rem; opacity: .7; }
.home-title { font-size: clamp(2rem, 5vw, 3.1rem); font-weight: 800; letter-spacing: -.045em; line-height: 1.08; margin: .25rem 0 .6rem; }
.home-title span { background: linear-gradient(90deg, var(--m-accent), var(--m-accent2)); -webkit-background-clip: text; background-clip: text; color: transparent; }
.home-lead { font-size: 1.05rem; line-height: 1.6; max-width: 46rem; opacity: .85; margin: 0; }
.home-card-title { font-weight: 800; font-size: 1.02rem; letter-spacing: -.02em; }
.home-card-text { font-size: .88rem; opacity: .75; line-height: 1.5; min-height: 4.6em; margin-top: 4px; }
.home-step { display: flex; gap: .8rem; align-items: flex-start; margin: .6rem 0; }
.home-step b.n { flex: 0 0 auto; width: 1.9rem; height: 1.9rem; border-radius: 50%; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--m-accent), #3b82f6); color: #fff; font-size: .9rem; }
[class*="st-key-card-feat-"] [data-testid="stPageLink-NavLink"] { border: 1px solid color-mix(in srgb, currentColor 20%, transparent); border-radius: 999px;
  justify-content: center; font-weight: 700; min-height: 40px; }
[class*="st-key-card-feat-"] [data-testid="stPageLink-NavLink"]:hover { background: var(--m-accent-soft); border-color: var(--m-accent); }

/* ---------- chuyển động nhẹ ---------- */
@keyframes ux-rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
[data-testid="stMain"] h1, .memora-title { animation: ux-rise .6s cubic-bezier(.2,.8,.2,1) backwards; }
[class*="st-key-card-"] { animation: ux-rise .7s cubic-bezier(.2,.8,.2,1) .06s backwards; }
@media (prefers-reduced-motion: reduce) { [data-testid="stMain"] h1, .memora-title, [class*="st-key-card-"] { animation: none; } }

/* ---------- điện thoại ---------- */
@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] { padding: 3.6rem .8rem 2rem !important; }
  .memora-title { font-size: 1.5rem; }
  [data-testid="stMain"] [data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"]:has([class*="st-key-card-kpi"]) > [data-testid="stColumn"] {
    min-width: calc(50% - .5rem) !important; flex: 1 1 calc(50% - .5rem) !important; }
  [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] { min-height: 44px; }
  [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
  [class*="st-key-card-"] { border-radius: 18px; padding: 16px; }
}
</style>
"""


def _is_dark() -> bool:
    try:
        return getattr(st.context.theme, "type", None) == "dark"
    except Exception:
        return False


def inject_css() -> None:
    tokens = DARK if _is_dark() else LIGHT
    root = ":root{" + "".join(f"--m-{k}:{v};" for k, v in tokens.items()) + "}"
    st.markdown(
        '<style>@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap");'
        + root + "</style>" + CSS,
        unsafe_allow_html=True,
    )


def esc(x) -> str:
    return html.escape(str(x))


def badge(text: str, kind: str = "") -> str:
    return f'<span class="memora-badge {kind}">{esc(text)}</span>'


def page_title(title: str, subtitle: str = "") -> None:
    st.markdown(f'<h1 class="memora-title">{esc(title)}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<p class="memora-subtitle">{esc(subtitle)}</p>', unsafe_allow_html=True)


def section(title: str, note: str = "") -> None:
    st.markdown(f'<div class="memora-section">{esc(title)}</div>', unsafe_allow_html=True)


def kpi_row(items: list[tuple[str, str, str | None]]) -> None:
    """items: (nhãn, giá trị, ghi chú hiện khi rê chuột) → một hàng thẻ số."""
    cols = st.columns(len(items))
    for i, (col, (label, value, note)) in enumerate(zip(cols, items)):
        with col.container(key=f"card-kpi-{i}"):
            st.metric(label, value, help=note)


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
        st.markdown(f'{badge("Sắp có", "doing")}<ul class="memora-soon-list">{items}</ul>', unsafe_allow_html=True)
