"""Tổng quan: lời chào, số liệu, lối tắt tới từng kỹ năng, band theo thời gian, đề đang làm dở."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from core import catalog as cat_mod
from core import db
from core.reading_nav import open_test
from core.session import current_user
from core.ui import badge, esc, kpi_row, progress_bar, section

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
user = current_user()
catalog = cat_mod.load_catalog()

tests = {t["id"]: {**t, "name": f"{s['title']} – {t['title']}"}
         for c in catalog["categories"] for s in c["series"] for t in s["tests"]}
attempts = db.list_attempts(user["id"], 500)         # mới nhất trước
progress = db.progress_summary(user["id"])
doing = [tid for tid, p in progress.items() if not p["submitted"] and tid in tests]

FEATURES = [
    ("views/reading.py", "Reading", ":material/menu_book:", "Làm đề trên giao diện thi máy: chia đôi màn hình, highlight, bấm giờ, chấm band tự động."),
    ("views/listening.py", "Listening", ":material/headphones:", "Nghe theo Section 1–4, có chế độ thi và chế độ luyện nghe lại."),
    ("views/writing.py", "Writing", ":material/edit_note:", "Viết Task 1 và Task 2 có đếm từ, đếm giờ, đối chiếu tiêu chí chấm."),
    ("views/speaking.py", "Speaking", ":material/mic:", "Ngân hàng câu hỏi Part 1, 2, 3 theo chủ đề kèm câu trả lời mẫu."),
    ("views/grammar.py", "Ngữ pháp", ":material/spellcheck:", "Học theo chủ điểm, làm bài tập và ôn lại những câu đã sai."),
]

st.html(f"""
<div>
  <div class="home-kicker">Xin chào, {esc(user['display_name'])}</div>
  <div class="home-title">Luyện IELTS cùng <span>Memora</span></div>
  <p class="home-lead">Làm đề trong môi trường giống phòng thi máy, lưu tiến độ theo tài khoản và theo dõi band của bạn qua từng lần làm bài.</p>
</div>""")

# ---- Số liệu ----
if attempts:
    bands = [float(a["band"]) for a in attempts]
    avg = round(sum(bands) / len(bands) * 2) / 2
    kpi_row([
        ("Bài đã nộp", str(len(attempts)), "Tổng số lần nộp bài Reading"),
        ("Band cao nhất", f"{max(bands):.1f}", None),
        ("Band trung bình", f"{avg:.1f}", "Làm tròn đến 0,5"),
        ("Đang làm dở", str(len(doing)), "Số đề đã bắt đầu nhưng chưa nộp"),
    ])
else:
    with st.container(key="card-empty-home"):
        st.markdown('<div class="memora-empty"><b>Bạn chưa nộp bài nào</b>'
                    '<p>Làm một đề Reading để xem điểm band và tiến độ ở đây.</p></div>', unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 1, 1])
        with mid:
            st.page_link("views/reading.py", label="Chọn đề Reading", icon=":material/arrow_forward:", width="stretch")

# ---- Đang làm dở ----
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

# ---- Band theo thời gian ----
if len(attempts) >= 2:
    section("Band theo từng lần làm")
    with st.container(key="card-chart"):
        df = pd.DataFrame({
            "Lần": list(range(1, len(attempts) + 1)),
            "Band": [float(a["band"]) for a in reversed(attempts)],
        }).set_index("Lần")
        st.line_chart(df, color="#2563eb", height=240)

# ---- Lối tắt tới từng kỹ năng ----
section("Luyện tập")
cols = st.columns(len(FEATURES))
for col, (path, title, icon, text) in zip(cols, FEATURES):
    with col.container(key=f"card-feat-{path.split('/')[-1][:-3]}"):
        st.html(f'<div class="home-card-title">{esc(title)}</div><div class="home-card-text">{esc(text)}</div>')
        st.page_link(path, label="Mở trang", icon=":material/arrow_forward:", width="stretch")

# ---- Lần làm gần đây ----
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

# ---- Cách dùng ----
section("Dùng thế nào?")
with st.container(key="card-how"):
    st.html("""
    <div class="home-step"><b class="n">1</b><div><b>Chọn đề</b><br>Vào Reading, chọn bộ đề và bấm Bắt đầu làm.</div></div>
    <div class="home-step"><b class="n">2</b><div><b>Làm bài như phòng thi máy</b><br>Bôi đen để highlight dẫn chứng, bấm giờ tự chạy, câu trả lời tự lưu.</div></div>
    <div class="home-step"><b class="n">3</b><div><b>Nộp bài và xem band</b><br>Điểm được chấm lại ở máy chủ rồi quy đổi sang band.</div></div>
    <div class="home-step"><b class="n">4</b><div><b>Theo dõi tiến bộ</b><br>Biểu đồ band ở trang này cập nhật sau mỗi lần nộp.</div></div>""")
