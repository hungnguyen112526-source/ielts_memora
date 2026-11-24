"""Reading: library of tests (by category → series → test) and the exam screen."""
import streamlit as st

from core import catalog as cat_mod
from core import db, scoring
from core.reader_component import reader
from core.reading_nav import close_test, open_test
from core.session import current_user
from core.ui import badge, page_title, type_label

user = current_user()
catalog = cat_mod.load_catalog()
SIGNATURE = catalog["signature"]


@st.cache_data(show_spinner=False)
def _cached_test(test_id: str, signature: int) -> dict | None:
    """Full test content, read from disk only when a test is opened (then cached)."""
    return cat_mod.load_test(cat_mod.load_catalog(), test_id)


# ------------------------------------------------------------------ library
def _status(test_id: str, progress: dict) -> str:
    p = progress.get(test_id)
    if not p:
        return "todo"
    return "done" if p["submitted"] else "doing"


def _test_card(t: dict, progress: dict, last_attempt: dict) -> None:
    status = _status(t["id"], progress)
    with st.container(border=True):
        if status == "done":
            a = last_attempt.get(t["id"])
            label = f"Đã nộp · Band {a['band']} ({a['score']}/{a['total']})" if a else "Đã nộp"
            st.markdown(badge(label, "done"), unsafe_allow_html=True)
        elif status == "doing":
            st.markdown(badge(f"Đang làm · {progress[t['id']]['answered']}/{t['totalQuestions']} câu", "doing"),
                        unsafe_allow_html=True)
        else:
            st.markdown(badge("Chưa làm", "todo"), unsafe_allow_html=True)

        st.markdown(f'<p class="memora-card-title">{t["title"]}</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="memora-card-sub">{" • ".join(t["passages"])}</p>', unsafe_allow_html=True)
        types = ", ".join(type_label(x) for x in t["questionTypes"])
        st.markdown(
            f'<p class="memora-meta">{t["durationMin"]} phút · {t["totalQuestions"]} câu<br>{types}</p>',
            unsafe_allow_html=True,
        )
        label = {"todo": "Làm bài", "doing": "Tiếp tục", "done": "Xem lại"}[status]
        if st.button(label, key=f"open-{t['id']}", type="primary" if status != "done" else "secondary"):
            open_test(t["id"])
            st.rerun()


def _matches(t: dict, query: str, status: str, progress: dict) -> bool:
    if status != "Tất cả" and {"Chưa làm": "todo", "Đang làm": "doing", "Đã nộp": "done"}[status] != _status(t["id"], progress):
        return False
    if query:
        hay = " ".join([t["title"], t["summary"], *t["passages"]]).lower()
        return query.lower() in hay
    return True


def library() -> None:
    page_title("Reading", "Chọn một bộ đề. Tiến độ và điểm số được lưu theo tài khoản của bạn.")
    progress = db.progress_summary(user["id"])
    last_attempt: dict[str, dict] = {}
    for a in db.list_attempts(user["id"], 1000):          # newest first
        last_attempt.setdefault(a["test_id"], a)

    c1, c2 = st.columns([2, 1])
    query = c1.text_input("Tìm đề", placeholder="Tìm theo tên bài đọc…", label_visibility="collapsed").strip()
    status = c2.selectbox("Trạng thái", ["Tất cả", "Chưa làm", "Đang làm", "Đã nộp"], label_visibility="collapsed")

    categories = catalog["categories"]
    for tab, cat in zip(st.tabs([c["title"] for c in categories]), categories):
        with tab:
            st.caption(cat["description"])
            if not cat["series"]:
                st.info("Chưa có đề trong mục này. Gửi tài liệu để thêm vào.")
                continue
            for series in cat["series"]:
                tests = [t for t in series["tests"] if _matches(t, query, status, progress)]
                if not tests:
                    continue
                done = sum(1 for t in series["tests"] if _status(t["id"], progress) == "done")
                has_doing = any(_status(t["id"], progress) == "doing" for t in series["tests"])
                expanded = len(cat["series"]) <= 3 or has_doing or bool(query)
                with st.expander(f"{series['title']} — {done}/{len(series['tests'])} đề đã nộp", expanded=expanded):
                    if series.get("description"):
                        st.caption(series["description"])
                    cols = st.columns(2)
                    for i, t in enumerate(tests):
                        with cols[i % 2]:
                            _test_card(t, progress, last_attempt)


# --------------------------------------------------------------------- exam
def _handle_event(val, test: dict) -> None:
    """Store what the exam engine reports. Scores are recomputed here, not trusted from the browser."""
    if not isinstance(val, dict) or val.get("testId") != test["id"]:
        return
    nonce = val.get("nonce")
    nonce_key = f"_nonce_{test['id']}"
    if not nonce or st.session_state.get(nonce_key) == nonce:
        return                                              # already processed (Streamlit reruns re-deliver it)
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
        pass                                                # a finished test stays locked until reset
    elif event == "submit":
        result = scoring.score_test(test, state["answers"])
        state.update(submitted=True, score=result["score"])
        db.save_progress(uid, tid, state)
        timeout = bool((val.get("result") or {}).get("timeout"))
        db.add_attempt(uid, tid, result["score"], result["total"], result["band"],
                       test["durationMin"] * 60 - state["timeLeft"],
                       {"byPassage": result["byPassage"], "timeout": timeout})
    elif event in ("autosave", "exit"):
        state["submitted"] = False                          # only "submit" can finish a test
        db.save_progress(uid, tid, state)

    if event == "exit":
        close_test()
        st.rerun()


def exam(test_id: str) -> None:
    entry = cat_mod.find_test_entry(catalog, test_id)
    test = _cached_test(test_id, SIGNATURE)
    prev_id, next_id = cat_mod.neighbours(catalog, test_id)

    top = st.columns([1.3, 3, 1.1, 1.1])
    if top[0].button("← Danh sách đề"):
        close_test()
        st.rerun()
    top[1].markdown(f"**{entry['series_title']}** — {entry['title']}")
    if top[2].button("‹ Đề trước", disabled=prev_id is None):
        open_test(prev_id)
        st.rerun()
    if top[3].button("Đề sau ›", disabled=next_id is None):
        open_test(next_id)
        st.rerun()

    opens = st.session_state.get("reading_opens", 0)
    val = reader(
        test=test,
        meta={"badge": next((s.get("badge") for c in catalog["categories"] for s in c["series"]
                             if s["id"] == entry["series_id"]), None) or "O",
              "seriesTitle": entry["series_title"]},
        saved=db.get_progress(user["id"], test_id),
        prefs=db.get_prefs(user["id"]),
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
