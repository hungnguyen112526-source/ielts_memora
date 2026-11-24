"""Dashboard: progress, band history, unfinished tests."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from core import catalog as cat_mod
from core import db
from core.reading_nav import open_test
from core.session import current_user
from core.ui import badge

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
user = current_user()
catalog = cat_mod.load_catalog()

names = {t["id"]: f"{s['title']} – {t['title']}"
         for c in catalog["categories"] for s in c["series"] for t in s["tests"]}
attempts = db.list_attempts(user["id"], 500)         # newest first
progress = db.progress_summary(user["id"])

st.markdown(f"## Xin chào, {user['display_name']}")
st.markdown('<p class="memora-muted">Tổng quan quá trình luyện Reading của bạn.</p>', unsafe_allow_html=True)

if not attempts:
    with st.container(border=True):
        st.markdown("**Bạn chưa nộp bài nào.** Bắt đầu với một đề Reading để xem điểm band và tiến độ ở đây.")
        if st.button("Chọn đề Reading", type="primary"):
            st.switch_page("views/reading.py")
else:
    bands = [float(a["band"]) for a in attempts]
    m1, m2, m3 = st.columns(3)
    m1.metric("Bài đã nộp", len(attempts))
    m2.metric("Band cao nhất", f"{max(bands):.1f}")
    m3.metric("Band trung bình", f"{round(sum(bands) / len(bands) * 2) / 2:.1f}")

    if len(attempts) >= 2:
        df = pd.DataFrame({
            "Lần": range(1, len(attempts) + 1),
            "Band": [float(a["band"]) for a in reversed(attempts)],
        }).set_index("Lần")
        st.markdown("#### Band theo từng lần làm")
        st.line_chart(df)

doing = [tid for tid, p in progress.items() if not p["submitted"] and tid in names]
if doing:
    st.markdown("#### Đang làm dở")
    for tid in doing:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{names[tid]}** &nbsp; {badge(str(progress[tid]['answered']) + ' câu đã trả lời', 'doing')}",
                        unsafe_allow_html=True)
            if c2.button("Tiếp tục", key=f"resume-{tid}", type="primary"):
                open_test(tid)
                st.switch_page("views/reading.py")

if attempts:
    st.markdown("#### Các lần làm gần đây")
    rows = []
    for a in attempts[:15]:
        mins, secs = divmod(a["seconds"], 60)
        rows.append({
            "Đề": names.get(a["test_id"], a["test_id"]),
            "Điểm": f"{a['score']}/{a['total']}",
            "Band": a["band"],
            "Thời gian": f"{mins}:{secs:02d}",
            "Ngày": datetime.fromtimestamp(a["created_at"], TZ).strftime("%d/%m/%Y %H:%M"),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True)
