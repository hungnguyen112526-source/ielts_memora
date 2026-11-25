"""Tổng quan: lời chào, số liệu, lối tắt tới từng kỹ năng, band theo thời gian, đề đang làm dở."""
from datetime import datetime
from zoneinfo import ZoneInfo

import altair as alt
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
all_attempts = [a for a in db.list_attempts(user["id"], 500) if a["valid"]]    # mới nhất trước, bỏ lượt trắng
attempts = [a for a in all_attempts if a["scope"] == "full"]                  # thống kê band chỉ tính cả đề
passage_attempts = [a for a in all_attempts if a["scope"] != "full"]
progress = db.progress_summary(user["id"])
doing = [k for k, p in progress.items() if not p["submitted"] and db.split_key(k)[0] in tests]


def _scope_total(t: dict, scope: str) -> int:
    if scope == "full":
        return t["totalQuestions"]
    rng = (t.get("qRanges") or [])[int(scope[1:]) - 1:int(scope[1:])]
    return rng[0][1] - rng[0][0] + 1 if rng else 0


def _scope_label(scope: str) -> str:
    return "Cả đề" if scope == "full" else f"Passage {scope[1:]}"

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
        ("Đề đã nộp", str(len(attempts)), "Số lần nộp cả đề Reading"),
        ("Band cao nhất", f"{max(bands):.1f}", None),
        ("Band trung bình", f"{avg:.1f}", "Làm tròn đến 0,5"),
        ("Đang làm dở", str(len(doing)), "Số đề đã bắt đầu nhưng chưa nộp"),
    ])
else:
    with st.container(key="card-empty-home"):
        st.markdown('<div class="memora-empty"><b>Bạn chưa nộp cả đề nào</b>'
                    '<p>Làm một đề Reading (hoặc từng passage) để xem kết quả và tiến độ ở đây.</p></div>', unsafe_allow_html=True)
        _, mid, _ = st.columns([1, 1, 1])
        with mid:
            st.page_link("views/reading.py", label="Chọn đề Reading", icon=":material/arrow_forward:", width="stretch")

# ---- Đang làm dở ----
if doing:
    section("Đang làm dở")
    cols = st.columns(2)
    for i, key in enumerate(doing):
        tid, scope = db.split_key(key)
        t, p = tests[tid], progress[key]
        total = _scope_total(t, scope)
        with cols[i % 2]:
            with st.container(key=f"card-doing-{i}"):
                st.markdown(
                    f'<div class="memora-card-head"><p class="memora-card-title">{esc(t["name"])} · {_scope_label(scope)}</p>'
                    f'{badge("Đang làm", "doing")}</div>'
                    f'<p class="memora-meta" style="padding:0">{p["answered"]}/{total} câu đã trả lời</p>'
                    f'{progress_bar(p["answered"], total)}',
                    unsafe_allow_html=True,
                )
                if st.button("Làm tiếp", key=f"resume-{i}", type="primary", width="stretch"):
                    open_test(tid, scope)
                    st.switch_page("views/reading.py")

# ---- Band theo thời gian ----
if len(attempts) >= 2:
    section("Band theo từng lần làm")
    with st.container(key="card-chart"):
        df = pd.DataFrame({
            "Lần": list(range(1, len(attempts) + 1)),
            "Band": [float(a["band"]) for a in reversed(attempts)],
        })
        chart = (alt.Chart(df).mark_line(point=True, color="#2563eb", strokeWidth=3)
                 .encode(x=alt.X("Lần:O", axis=alt.Axis(labelAngle=0)),
                         y=alt.Y("Band:Q", scale=alt.Scale(domain=[0, 9]), axis=alt.Axis(tickCount=9)),
                         tooltip=["Lần", "Band"])
                 .properties(height=240))
        st.altair_chart(chart, width="stretch")

# ---- Passage lẻ ----
if passage_attempts:
    section("Làm từng passage", "Độ chính xác = số câu đúng / số câu của passage")
    rate = [a["score"] / a["total"] for a in passage_attempts if a["total"]]
    kpi_row([
        ("Passage đã làm", str(len(passage_attempts)), None),
        ("Độ chính xác trung bình", f"{round(sum(rate) / len(rate) * 100)}%", None),
        ("Tốt nhất", f"{round(max(rate) * 100)}%", None),
    ], prefix="p")

# ---- Lối tắt tới từng kỹ năng ----
section("Luyện tập")
cols = st.columns(len(FEATURES))
for col, (path, title, icon, text) in zip(cols, FEATURES):
    with col.container(key=f"card-feat-{path.split('/')[-1][:-3]}"):
        st.html(f'<div class="home-card-title">{esc(title)}</div><div class="home-card-text">{esc(text)}</div>')
        st.page_link(path, label="Mở trang", icon=":material/arrow_forward:", width="stretch")

# ---- Lần làm gần đây ----
if all_attempts:
    section("Các lần làm gần đây")
    rows = []
    for a in all_attempts[:15]:
        mins, secs = divmod(a["seconds"], 60)
        when = datetime.fromtimestamp(a["created_at"], TZ).strftime("%d/%m/%Y %H:%M")
        name = tests.get(a["test_id"], {}).get("name", a["test_id"])
        rows.append(
            f'<tr><td class="name">{esc(name)}</td><td>{_scope_label(a["scope"])}</td>'
            f'<td class="num">{a["score"]}/{a["total"]}</td>'
            f'<td>{badge(str(a["band"]), "done") if a["band"] else "–"}</td><td class="num">{mins}:{secs:02d}</td>'
            f'<td class="num">{when}</td></tr>'
        )
    with st.container(key="card-recent"):
        st.markdown(
            '<div style="overflow-x:auto"><table class="memora-table"><thead><tr>'
            '<th>Đề</th><th>Phạm vi</th><th>Điểm</th><th>Band</th><th>Thời gian</th><th>Ngày</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>',
            unsafe_allow_html=True,
        )

# ---- Cách dùng ----
section("Dùng thế nào?")
with st.container(key="card-how"):
    st.html("""
    <div class="home-step"><b class="n">1</b><div><b>Chọn đề hoặc từng passage</b><br>Vào Reading, làm cả đề hoặc chỉ một passage bạn muốn luyện.</div></div>
    <div class="home-step"><b class="n">2</b><div><b>Làm bài như phòng thi máy</b><br>Bôi đen để highlight dẫn chứng, bấm giờ tự chạy, câu trả lời tự lưu.</div></div>
    <div class="home-step"><b class="n">3</b><div><b>Nộp bài và xem điểm</b><br>Cả đề được quy đổi sang band; passage lẻ cho số câu đúng và độ chính xác.</div></div>
    <div class="home-step"><b class="n">4</b><div><b>Theo dõi tiến bộ</b><br>Biểu đồ band ở trang này cập nhật sau mỗi lần nộp.</div></div>""")
