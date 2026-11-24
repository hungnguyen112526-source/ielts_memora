"""Tổng quan: số liệu, band theo thời gian, đề đang làm dở, các lần làm gần đây."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from core import catalog as cat_mod
from core import db
from core.reading_nav import open_test
from core.session import current_user
from core.ui import badge, esc, page_title, progress_bar, section, stat_card

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
user = current_user()
catalog = cat_mod.load_catalog()

tests = {t["id"]: {**t, "name": f"{s['title']} – {t['title']}"}
         for c in catalog["categories"] for s in c["series"] for t in s["tests"]}
attempts = db.list_attempts(user["id"], 500)         # mới nhất trước
progress = db.progress_summary(user["id"])

page_title(f"Xin chào, {user['display_name']}", "Tổng quan quá trình luyện Reading của bạn.")

if not attempts:
    with st.container(key="card-empty-home"):
        st.markdown('<div class="memora-empty"><b>Bạn chưa nộp bài nào</b>'
                    '<p>Làm một đề Reading để xem điểm band và tiến độ ở đây.</p></div>',
                    unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 1, 1])
        if mid.button("Chọn đề Reading", type="primary", width="stretch"):
            st.switch_page("views/reading.py")
else:
    bands = [float(a["band"]) for a in attempts]
    avg = round(sum(bands) / len(bands) * 2) / 2
    c1, c2, c3 = st.columns(3)
    c1.markdown(stat_card("Bài đã nộp", len(attempts)), unsafe_allow_html=True)
    c2.markdown(stat_card("Band cao nhất", f"{max(bands):.1f}", accent=True), unsafe_allow_html=True)
    c3.markdown(stat_card("Band trung bình", f"{avg:.1f}"), unsafe_allow_html=True)

    if len(attempts) >= 2:
        section("Band theo từng lần làm")
        with st.container(key="card-chart"):
            df = pd.DataFrame({
                "Lần": list(range(1, len(attempts) + 1)),
                "Band": [float(a["band"]) for a in reversed(attempts)],
            }).set_index("Lần")
            st.line_chart(df, color="#2563eb", height=240)

doing = [tid for tid, p in progress.items() if not p["submitted"] and tid in tests]
if doing:
    section("Đang làm dở")
    cols = st.columns(2)
    for i, tid in enumerate(doing):
        t, p = tests[tid], progress[tid]
        with cols[i % 2]:
            with st.container(key=f"card-doing-{tid}"):
                st.markdown(
                    f'<div class="memora-card-head"><p class="memora-card-title">{esc(t["name"])}</p>'
                    f'{badge("Đang làm", "doing")}</div>'
                    f'<p class="memora-meta" style="padding:0">{p["answered"]}/{t["totalQuestions"]} câu đã trả lời</p>'
                    f'{progress_bar(p["answered"], t["totalQuestions"])}',
                    unsafe_allow_html=True,
                )
                if st.button("Làm tiếp", key=f"resume-{tid}", type="primary", width="stretch"):
                    open_test(tid)
                    st.switch_page("views/reading.py")

if attempts:
    section("Các lần làm gần đây")
    rows = []
    for a in attempts[:15]:
        mins, secs = divmod(a["seconds"], 60)
        when = datetime.fromtimestamp(a["created_at"], TZ).strftime("%d/%m/%Y %H:%M")
        name = tests.get(a["test_id"], {}).get("name", a["test_id"])
        rows.append(
            f'<tr><td class="name">{esc(name)}</td><td class="num">{a["score"]}/{a["total"]}</td>'
            f'<td>{badge(str(a["band"]), "done")}</td><td class="num">{mins}:{secs:02d}</td>'
            f'<td class="num">{when}</td></tr>'
        )
    with st.container(key="card-recent"):
        st.markdown(
            '<div style="overflow-x:auto"><table class="memora-table"><thead><tr>'
            '<th>Đề</th><th>Điểm</th><th>Band</th><th>Thời gian</th><th>Ngày</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>',
            unsafe_allow_html=True,
        )
