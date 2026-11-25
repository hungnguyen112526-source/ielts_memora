"""Reading: thư viện đề (danh mục → bộ → đề) và màn làm bài."""
import streamlit as st

from core import catalog as cat_mod
from core import db, scoring
from core.reader_component import reader
from core.reading_nav import close_test, open_test
from core.session import current_user
from core.ui import badge, esc, page_title, type_label

user = current_user()
catalog = cat_mod.load_catalog()
SIGNATURE = catalog["signature"]

# Màn làm bài chiếm trọn chiều cao cửa sổ: bỏ padding của Streamlit, iframe cao bằng màn hình.
EXAM_CSS = """
<style>
.block-container, [data-testid="stMainBlockContainer"] { max-width: 100% !important; padding: 2.5rem .75rem 0 !important; }
[data-testid="stVerticalBlock"] { gap: 0 !important; }
iframe[title*="memora_reader"] { height: calc(100vh - 3.4rem) !important; min-height: 540px;
  border: 1px solid #e2e8f0; border-radius: 16px; background: #fff; }
</style>
"""

LIBRARY_CSS = """
<style>
.memora-series { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  margin: 1.5rem 0 .25rem; }
.memora-series h3 { font-size: 1.15rem; font-weight: 800; margin: 0; padding: 0; color: #0f172a; }
.memora-series span { font-size: .82rem; font-weight: 700; color: #1d4ed8; background: #eff6ff; padding: 3px 10px; border-radius: 8px; }
.memora-series-desc { color: #64748b; font-size: .88rem; margin: 0 0 .75rem; }
</style>
"""


@st.cache_data(show_spinner=False)
def _cached_test(test_id: str, signature: int) -> dict | None:
    """Nội dung đầy đủ của đề, chỉ đọc từ đĩa khi mở đề (rồi cache)."""
    return cat_mod.load_test(cat_mod.load_catalog(), test_id)


# ------------------------------------------------------------------ library
def _status(test_id: str, progress: dict) -> str:
    p = progress.get(test_id)
    if not p:
        return "todo"
    return "done" if p["submitted"] else "doing"


def _test_card(t: dict, progress: dict, last_attempt: dict) -> None:
    status = _status(t["id"], progress)
    if status == "done":
        a = last_attempt.get(t["id"])
        tag = badge(f"Band {a['band']} ({a['score']}/{a['total']})", "done") if a else badge("Đã nộp", "done")
    elif status == "doing":
        tag = badge(f"Đang làm ({progress[t['id']]['answered']}/{t['totalQuestions']})", "doing")
    else:
        tag = badge("Chưa làm", "todo")

    plist = "".join(f"<li><b>P{i}</b><span>{esc(title)}</span></li>" for i, title in enumerate(t["passages"], 1))
    types = " · ".join(type_label(x) for x in t["questionTypes"])
    with st.container(key=f"card-test-{t['id']}"):
        st.markdown(
            f'<div class="memora-card-head"><p class="memora-card-title">{esc(t["title"])}</p>{tag}</div>'
            f'<ul class="memora-plist">{plist}</ul>',
            unsafe_allow_html=True,
        )
        left, right = st.columns([1.5, 1], vertical_alignment="center")
        types_line = f"<br>{esc(types)}" if types else ""
        left.markdown(f'<p class="memora-meta">{t["durationMin"]} phút · {t["totalQuestions"]} câu{types_line}</p>',
                      unsafe_allow_html=True)
        label = {"todo": "Bắt đầu làm", "doing": "Làm tiếp", "done": "Xem lại"}[status]
        if right.button(label, key=f"open-{t['id']}", type="primary" if status != "done" else "secondary",
                        width="stretch"):
            open_test(t["id"])
            st.rerun()


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
    st.markdown(LIBRARY_CSS, unsafe_allow_html=True)
    page_title("Reading", "Chọn một bộ đề. Tiến độ và điểm số được lưu theo tài khoản của bạn.")
    progress = db.progress_summary(user["id"])
    last_attempt: dict[str, dict] = {}
    for a in db.list_attempts(user["id"], 1000):          # mới nhất trước
        last_attempt.setdefault(a["test_id"], a)

    c1, c2 = st.columns([1.2, 1.5], vertical_alignment="center")
    query = c1.text_input("Tìm đề", placeholder="Tìm theo tên bài đọc…", icon=":material/search:",
                          label_visibility="collapsed").strip()
    status = c2.segmented_control("Trạng thái", list(FILTERS), default="Tất cả",
                                  label_visibility="collapsed") or "Tất cả"

    categories = catalog["categories"]
    for tab, cat in zip(st.tabs([c["title"] for c in categories]), categories):
        with tab:
            if cat.get("description"):
                st.markdown(f'<p class="memora-muted" style="margin-top:.75rem">{esc(cat["description"])}</p>',
                            unsafe_allow_html=True)
            if not cat["series"]:
                with st.container(key=f"card-empty-{cat['id']}"):
                    st.markdown('<div class="memora-empty"><b>Chưa có đề trong mục này</b>'
                                '<p>Đề mới sẽ xuất hiện ở đây ngay khi được thêm vào.</p></div>',
                                unsafe_allow_html=True)
                continue
            shown = 0
            for series in cat["series"]:
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
                                '<p>Thử bỏ bộ lọc trạng thái hoặc tìm bằng từ khóa khác.</p></div>',
                                unsafe_allow_html=True)


# --------------------------------------------------------------------- exam
def _handle_event(val, test: dict) -> None:
    """Lưu những gì engine báo về. Điểm được chấm lại ở server, không tin điểm từ trình duyệt."""
    if not isinstance(val, dict) or val.get("testId") != test["id"]:
        return
    nonce = val.get("nonce")
    nonce_key = f"_nonce_{test['id']}"
    if not nonce or st.session_state.get(nonce_key) == nonce:
        return                                              # đã xử lý (Streamlit rerun gửi lại event)
    st.session_state[nonce_key] = nonce

    uid, tid = user["id"], test["id"]
    event = val.get("event")
    state = scoring.clean_state(test, val.get("state"))
    existing = db.get_progress(uid, tid)

    prefs = val.get("prefs")
    if isinstance(prefs, dict):
        size = prefs.get("fontSize")
        db.save_prefs(uid, {"darkMode": bool(prefs.get("darkMode")),
                            "fontSize": min(22, max(13, size)) if isinstance(size, (int, float)) else 15})

    if event == "reset":
        db.delete_progress(uid, tid)
    elif existing and existing.get("submitted"):
        pass                                                # đề đã nộp thì khóa cho tới khi làm lại
    elif event == "submit":
        result = scoring.score_test(test, state["answers"])
        state.update(submitted=True, score=result["score"])
        db.save_progress(uid, tid, state)
        timeout = bool((val.get("result") or {}).get("timeout"))
        db.add_attempt(uid, tid, result["score"], result["total"], result["band"],
                       test["durationMin"] * 60 - state["timeLeft"],
                       {"byPassage": result["byPassage"], "timeout": timeout})
    elif event in ("autosave", "exit", "prev", "next"):
        state["submitted"] = False                          # chỉ "submit" mới kết thúc bài
        db.save_progress(uid, tid, state)

    if event == "exit":
        close_test()
        st.rerun()
    if event in ("prev", "next"):
        prev_id, next_id = cat_mod.neighbours(catalog, tid)
        target = prev_id if event == "prev" else next_id
        if target:
            open_test(target)
            st.rerun()


def exam(test_id: str) -> None:
    st.markdown(EXAM_CSS, unsafe_allow_html=True)
    entry = cat_mod.find_test_entry(catalog, test_id)
    test = _cached_test(test_id, SIGNATURE)
    prev_id, next_id = cat_mod.neighbours(catalog, test_id)

    opens = st.session_state.get("reading_opens", 0)
    val = reader(
        test=test,
        meta={"badge": next((s.get("badge") for c in catalog["categories"] for s in c["series"]
                             if s["id"] == entry["series_id"]), None) or "O",
              "seriesTitle": entry["series_title"]},
        saved=db.get_progress(user["id"], test_id),
        prefs=db.get_prefs(user["id"]),
        nav={"prev": prev_id is not None, "next": next_id is not None},
        session_key=f"{test_id}:{opens}",
        key=f"reader-{test_id}-{opens}",
    )
    _handle_event(val, test)


selected = st.session_state.get("reading_test")
if selected and cat_mod.find_test_entry(catalog, selected):
    exam(selected)
else:
    close_test()
    library()
