"""Reading: thư viện đề (danh mục → bộ → đề) và màn làm bài."""
import uuid

import streamlit as st

from core import catalog as cat_mod
from core import db, exam_events, scoring
from core.reader_component import reader
from core.reading_nav import close_test, current_category, open_test
from core.session import current_user
from core.ui import badge, esc, page_title, progress_bar, type_label

user = current_user()
catalog = cat_mod.load_catalog()
SIGNATURE = catalog["signature"]

# Màn làm bài chiếm trọn chiều cao cửa sổ: bỏ padding của Streamlit, iframe cao bằng màn hình.
EXAM_CSS = """
<style>
.block-container, [data-testid="stMainBlockContainer"] { max-width: 100% !important; padding: .6rem .75rem 0 !important; }
/* Mỗi lần Streamlit chạy lại (autosave) nó làm mờ phần tử "cũ" xuống 33% nếu chạy quá 0,5s -> màn hình bài thi tối lại. Tắt hẳn ở màn làm bài. */
[data-stale="true"] { opacity: 1 !important; transition: none !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
/* Màn làm bài: bỏ thanh công cụ Streamlit (Share, sao, GitHub, ⋮) để dành chỗ; thoát bằng nút "Danh sách đề" */
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none !important; }
iframe[title*="memora_reader"] { height: calc(100vh - 1.6rem) !important; height: calc(100dvh - 1.6rem) !important; min-height: 540px;
  border: 1px solid var(--m-line); border-radius: 18px; background: transparent; overflow: hidden; }
</style>
"""

@st.cache_data(show_spinner=False)
def _cached_test(test_id: str, signature: int) -> dict | None:
    """Nội dung đầy đủ của đề, chỉ đọc từ đĩa khi mở đề (rồi cache)."""
    return cat_mod.load_test(cat_mod.load_catalog(), test_id)


# ------------------------------------------------------------------ library
def _status(key: str, progress: dict) -> str:
    """key = db.pkey(test_id, scope)."""
    p = progress.get(key)
    if not p:
        return "todo"
    return "done" if p["submitted"] else "doing"


@st.dialog("Chi tiết đề", width="large")
def _detail_dialog(t: dict, status: str, attempt: dict | None, answered: int) -> None:
    st.markdown(f'<p class="memora-card-title" style="font-size:1.25rem">{esc(t["title"])}</p>', unsafe_allow_html=True)
    if t.get("summary"):
        st.caption(t["summary"])
    if status == "done" and attempt:
        st.markdown(badge(f"Đã nộp · Band {attempt['band']} ({attempt['score']}/{attempt['total']})", "done"), unsafe_allow_html=True)
    elif status == "doing":
        st.markdown(badge(f"Đang làm · {answered}/{t['totalQuestions']} câu", "doing"), unsafe_allow_html=True)
        st.markdown(progress_bar(answered, t["totalQuestions"]), unsafe_allow_html=True)
    plist = "".join(f"<li><b>P{i}</b><span style='white-space:normal'>{esc(x)}</span></li>" for i, x in enumerate(t["passages"], 1))
    st.markdown(f'<ul class="memora-plist">{plist}</ul>', unsafe_allow_html=True)
    st.markdown(f'<p class="memora-meta">{t["durationMin"]} phút · {t["totalQuestions"]} câu</p>', unsafe_allow_html=True)
    if t["questionTypes"]:
        st.markdown(" ".join(badge(type_label(x)) for x in t["questionTypes"]), unsafe_allow_html=True)
    label = {"todo": "Bắt đầu làm", "doing": "Làm tiếp", "done": "Xem lại"}[status]
    if st.button(label, key=f"dlg-open-{t['id']}", type="primary", width="stretch"):
        open_test(t["id"])
        st.rerun()


def _qcount(t: dict, i: int) -> int:
    """Số câu của passage thứ i (0-based)."""
    rng = (t.get("qRanges") or [])[i:i + 1]
    return rng[0][1] - rng[0][0] + 1 if rng else 0


def _test_card(t: dict, progress: dict, last_attempt: dict) -> None:
    status = _status(t["id"], progress)
    attempt = last_attempt.get((t["id"], "full"))
    answered = progress.get(t["id"], {}).get("answered", 0)
    if status == "done":
        tag = badge(f"Band {attempt['band']} ({attempt['score']}/{attempt['total']})", "done") if attempt and attempt["band"] else badge("Đã nộp", "done")
    elif status == "doing":
        tag = badge(f"Đang làm ({answered}/{t['totalQuestions']})", "doing")
    else:
        tag = badge("Chưa làm", "todo")

    with st.container(key=f"card-test-{t['id']}"):
        st.markdown(f'<div class="memora-card-head"><p class="memora-card-title">{esc(t["title"])}</p>{tag}</div>',
                    unsafe_allow_html=True)
        for i, title in enumerate(t["passages"], 1):         # mỗi passage làm riêng được, có điểm riêng
            scope = f"p{i}"
            ps = _status(db.pkey(t["id"], scope), progress)
            pa = last_attempt.get((t["id"], scope))
            n = _qcount(t, i - 1)
            c_title, c_btn = st.columns([3.1, 1.3], vertical_alignment="center")
            c_title.markdown(f'<ul class="memora-plist"><li><b>P{i}</b><span>{esc(title)}</span></li></ul>',
                             unsafe_allow_html=True)
            if ps == "done":
                label = f"{pa['score']}/{pa['total']}" if pa else "Xem lại"
                icon = ":material/check_circle:"
            elif ps == "doing":
                label, icon = f"Tiếp {progress[db.pkey(t['id'], scope)]['answered']}/{n}", None
            else:
                label, icon = "Làm", None
            # on_click: callback chạy trước phần thân script nên vào thẳng bài thi, không dựng lại thư viện đề rồi mới rerun
            c_btn.button(label, key=f"pbtn-{t['id']}-{i}", icon=icon, type="secondary", width="stretch",
                         help=f"Chỉ làm Passage {i}, chấm điểm riêng", on_click=open_test, args=(t["id"], scope))
        c_meta, c_info, c_go = st.columns([1.1, 1, 1.45], vertical_alignment="center")
        c_meta.markdown(f'<p class="memora-meta">{t["durationMin"]} phút · {t["totalQuestions"]} câu</p>',
                        unsafe_allow_html=True)
        if c_info.button("Chi tiết", key=f"info-{t['id']}", type="tertiary", width="stretch"):
            _detail_dialog(t, status, attempt, answered)
        label = {"todo": "Làm cả đề", "doing": "Làm tiếp cả đề", "done": "Xem lại cả đề"}[status]
        c_go.button(label, key=f"open-{t['id']}", type="primary" if status != "done" else "secondary",
                    width="stretch", on_click=open_test, args=(t["id"],))


FILTERS = {"Tất cả": None, "Chưa làm": "todo", "Đang làm": "doing", "Đã nộp": "done"}


def _matches(t: dict, query: str, status: str, progress: dict) -> bool:
    wanted = FILTERS.get(status)
    if wanted and wanted != _status(t["id"], progress):
        return False
    if query:
        hay = " ".join([t["title"], t["summary"], *t["passages"]]).lower()
        return query.lower() in hay
    return True


def library() -> None:
    cat = current_category(catalog)
    page_title(f"Reading · {cat['title']}",
               cat.get("description") or "Chọn một bộ đề. Tiến độ và điểm số được lưu theo tài khoản của bạn.")
    progress = db.progress_summary(user["id"])
    last_attempt = db.last_attempts(user["id"])           # (đề, phạm vi) -> lượt mới nhất, không tải chi tiết

    names = {t["id"]: t for c in catalog["categories"] for sr in c["series"] for t in sr["tests"]}
    resume = sorted((k for k, p in progress.items() if not p["submitted"] and db.split_key(k)[0] in names),
                    key=lambda k: progress[k]["updated_at"], reverse=True)
    if resume:
        key = resume[0]
        tid, scope = db.split_key(key)
        t = names[tid]
        if scope == "full":
            what, total = t["title"], t["totalQuestions"]
        else:
            what, total = f"{t['title']} · Passage {scope[1:]}", _qcount(t, int(scope[1:]) - 1)
        with st.container(key="card-resume"):
            r1, r2 = st.columns([3, 1], vertical_alignment="center")
            r1.markdown(f'<p class="memora-card-title">Bạn đang làm dở: {esc(what)}</p>'
                        f'<p class="memora-meta" style="padding:0">{progress[key]["answered"]}/{total} câu đã trả lời</p>',
                        unsafe_allow_html=True)
            r2.button("Làm tiếp", key="resume-top", type="primary", width="stretch",
                      on_click=open_test, args=(tid, scope))

    by_topic = bool(cat.get("filterByTopic")) and bool(cat["series"])       # Band 4–5.0 / 5–6.5: mỗi "bộ" là một chủ đề
    c1, c2 = st.columns([1.2, 1.5], vertical_alignment="center")
    query = c1.text_input("Tìm đề", placeholder="Tìm theo tên bài đọc…", icon=":material/search:",
                          label_visibility="collapsed").strip()
    status = c2.segmented_control("Trạng thái", list(FILTERS), default="Tất cả",
                                  label_visibility="collapsed") or "Tất cả"

    topic = None
    topic_title = ""
    if by_topic:
        tkey = f"topic-{cat['id']}"
        topic = st.session_state.get(tkey) or None
        if topic not in {s["id"] for s in cat["series"]}:
            topic = None
        total_n = sum(len(s["tests"]) for s in cat["series"])
        tiles = [("", "Tất cả chủ đề", total_n)] + [(s["id"], s["title"], len(s["tests"])) for s in cat["series"]]

        def _pick(value: str, key: str = tkey) -> None:
            st.session_state[key] = value

        st.markdown('<p class="memora-meta" style="padding:.2rem 0 .1rem;font-weight:700">Chọn chủ đề</p>', unsafe_allow_html=True)
        with st.container(key=f"topic-grid-{cat['id']}"):
            for row_start in range(0, len(tiles), 3):
                cols = st.columns(3)
                for col, (sid, title, n) in zip(cols, tiles[row_start:row_start + 3]):
                    col.button(f"{title} ({n})", key=f"{tkey}-{sid or 'all'}", width="stretch",
                               type="primary" if (topic or "") == sid else "secondary",
                               on_click=_pick, args=(sid,))
        topic_title = next((s["title"] for s in cat["series"] if s["id"] == topic), "")

    shown = 0
    scope_tests = [t for s in cat["series"] if not topic or s["id"] == topic for t in s["tests"]]
    if not scope_tests:
        what = f"chủ đề {topic_title}" if topic_title else "mục này"
        with st.container(key=f"card-empty-{cat['id']}"):
            st.markdown(f'<div class="memora-empty"><b>Chưa có đề trong {esc(what)}</b>'
                        '<p>Đề mới sẽ xuất hiện ở đây ngay khi được thêm vào.</p></div>',
                        unsafe_allow_html=True)
        return
    for series in cat["series"]:
        if topic and series["id"] != topic:
            continue
        tests = [t for t in series["tests"] if _matches(t, query, status, progress)]
        if not tests:
            continue
        shown += 1
        done = sum(1 for t in series["tests"] if _status(t["id"], progress) == "done")
        st.markdown(
            f'<div class="memora-series"><h3>{esc(series["title"])}</h3>'
            f'<span>{done}/{len(series["tests"])} đề đã nộp</span></div>',
            unsafe_allow_html=True,
        )
        if series.get("description"):
            st.markdown(f'<p class="memora-series-desc">{esc(series["description"])}</p>', unsafe_allow_html=True)
        cols = st.columns(2)
        for i, t in enumerate(tests):
            with cols[i % 2]:
                _test_card(t, progress, last_attempt)
    if not shown:
        with st.container(key=f"card-nomatch-{cat['id']}"):
            st.markdown('<div class="memora-empty"><b>Không tìm thấy đề phù hợp</b>'
                        '<p>Thử đổi chủ đề, bỏ bộ lọc trạng thái hoặc tìm bằng từ khóa khác.</p></div>',
                        unsafe_allow_html=True)


# --------------------------------------------------------------------- exam
def _open_payload(test: dict, scope: str) -> dict:
    """Dữ liệu cho một lần mở đề: đọc DB đúng MỘT lần. Các lần Streamlit chạy lại sau đó (autosave) dùng lại bản này,
    không truy vấn lại. `revealed` = đã được xem đáp án (bài đã nộp)."""
    open_id = st.session_state.get("reading_open_id")
    pay = st.session_state.get("_reading_payload")
    if pay and pay["open_id"] == open_id and pay["uid"] == user["id"] and pay["test_id"] == test["id"] and pay["scope"] == scope:
        return pay
    if not open_id:
        open_id = st.session_state["reading_open_id"] = uuid.uuid4().hex
    saved = db.get_progress(user["id"], db.pkey(test["id"], scope))
    pay = {"open_id": open_id, "uid": user["id"], "test_id": test["id"], "scope": scope, "saved": saved,
           "prefs": db.get_prefs(user["id"]), "revealed": bool(saved and saved.get("submitted")), "nonce": None}
    st.session_state["_reading_payload"] = pay
    return pay


def _handle_event(val, test: dict, scope: str, pay: dict) -> None:
    """Ghi những gì engine báo về (logic ở core/exam_events.py) rồi làm các việc giao diện: thông báo, thoát, chuyển đề."""
    res = exam_events.process(user["id"], test, scope, val, pay)
    if res is None:
        return
    event = res["event"]
    if res["toast"]:
        st.toast(res["toast"][0], icon=res["toast"][1])
    if event == "cancel":
        close_test()
        st.rerun()
    if event == "exit":
        close_test()
        st.toast("Đã lưu tiến độ", icon="💾")
        st.rerun()
    if event in ("prev", "next"):
        prev_id, next_id = cat_mod.neighbours(catalog, test["id"])
        target = prev_id if event == "prev" else next_id
        if target:
            entry = cat_mod.find_test_entry(catalog, target)
            target_scope = scope if scope == "full" or int(scope[1:]) <= len(entry["passages"]) else "full"
            open_test(target, target_scope)
            st.toast("Đã lưu tiến độ đề trước", icon="💾")
            st.rerun()
    if res["reveal"]:
        st.rerun()                                          # chạy lại một lần để gửi đáp án + lời giải xuống engine


def _theme_type() -> str | None:
    try:
        return st.context.theme.type            # "light" | "dark" (Streamlit >= 1.46)
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def _cached_expl(test_id: str, signature: int) -> dict:
    return cat_mod.load_explanations(test_id)


def exam(test_id: str) -> None:
    st.markdown(EXAM_CSS, unsafe_allow_html=True)
    entry = cat_mod.find_test_entry(catalog, test_id)
    test = _cached_test(test_id, SIGNATURE)
    scope = scoring.parse_scope(test, st.session_state.get("reading_scope"))[0]
    prev_id, next_id = cat_mod.neighbours(catalog, test_id)
    pay = _open_payload(test, scope)
    open_id = pay["open_id"]

    # Khi đang làm, đề gửi xuống trình duyệt KHÔNG có đáp án; đáp án + lời giải chỉ gửi sau khi nộp.
    reveal = scoring.reveal_payload(test, _cached_expl(test_id, SIGNATURE)) if pay["revealed"] else None
    val = reader(
        test=scoring.public_test(test),
        meta={"badge": next((s.get("badge") for c in catalog["categories"] for s in c["series"]
                             if s["id"] == entry["series_id"]), None) or "O",
              "seriesTitle": entry["series_title"], "uid": user["id"]},
        saved=pay["saved"],
        prefs=pay["prefs"],
        scope=scope,
        theme=_theme_type(),
        nav={"prev": prev_id is not None, "next": next_id is not None},
        reveal=reveal,
        session_key=open_id,
        key=f"reader-{open_id}",
    )
    _handle_event(val, test, scope, pay)


selected = st.session_state.get("reading_test")
if selected and cat_mod.find_test_entry(catalog, selected):
    exam(selected)
else:
    close_test()
    library()
