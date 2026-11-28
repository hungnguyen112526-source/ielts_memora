"""Xử lý sự kiện bài thi (server), lưu tiến độ không ghi đè bài đã nộp, ẩn đáp án, lời giải."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import auth, catalog, db, exam_events, scoring  # noqa: E402

TEST_FILE = Path(__file__).resolve().parent.parent / "data/reading/band_4_5/education/test-1.json"


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORA_DB", str(tmp_path / "t.db"))
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db.init_db()
    ok, _, uid = auth.register("hocvien", "Học viên", "matkhau123", "matkhau123")
    assert ok
    test = json.loads(TEST_FILE.read_text(encoding="utf-8"))
    return uid, test, {"nonce": None, "prefs": {}, "saved": None, "revealed": False}


def good_answers(test, n):
    return {str(q): test["answers"][str(q)][0] for q in range(1, n + 1)}


def ev(test, event, answers, nonce, submitted=False, **extra):
    state = {"answers": answers, "submitted": submitted, "configured": True, "limit": 3600, "spent": 100,
             "passage": 0, "hl": {}, "ts": 5, "score": 40}      # score do trình duyệt báo (giả) phải bị bỏ qua
    return {"nonce": nonce, "event": event, "testId": test["id"], "scope": "full", "state": state, **extra}


# ----------------------------------------------------------------------------- db
def test_save_progress_if_open_never_overwrites_submitted(env):
    uid, test, _ = env
    assert db.save_progress_if_open(uid, test["id"], {"answers": {"1": "a"}, "submitted": False}) is True
    assert db.save_progress_if_open(uid, test["id"], {"answers": {"1": "b"}, "submitted": True}) is True
    assert db.save_progress_if_open(uid, test["id"], {"answers": {"1": "c"}, "submitted": False}) is False
    assert db.get_progress(uid, test["id"])["answers"] == {"1": "b"}


def test_last_attempts_returns_latest_per_scope(env):
    uid, test, _ = env
    db.add_attempt(uid, test["id"], 10, 40, "4.0", 100, {}, scope="full", created_at=100)
    db.add_attempt(uid, test["id"], 20, 40, "5.5", 100, {}, scope="full", created_at=200)
    db.add_attempt(uid, test["id"], 5, 13, "", 50, {}, scope="p1", created_at=150)
    last = db.last_attempts(uid)
    assert last[(test["id"], "full")]["score"] == 20 and last[(test["id"], "p1")]["score"] == 5
    assert len(last) == 2


def test_is_active_follows_block_and_delete(env):
    uid, _, _ = env
    assert auth.is_active(uid)
    auth.set_status(uid, "blocked")
    assert not auth.is_active(uid)
    auth.delete_user(uid)
    assert not auth.is_active(uid)


# ------------------------------------------------------------------- sự kiện bài thi
def test_autosave_saves_and_duplicate_nonce_is_ignored(env):
    uid, test, pay = env
    assert exam_events.process(uid, test, "full", ev(test, "autosave", {"1": "TRUE"}, "n1"), pay) is not None
    assert db.get_progress(uid, test["id"])["answers"] == {"1": "TRUE"}
    assert exam_events.process(uid, test, "full", ev(test, "autosave", {"1": "FALSE"}, "n1"), pay) is None   # cùng nonce
    assert db.get_progress(uid, test["id"])["answers"] == {"1": "TRUE"}


def test_submit_is_scored_on_server_and_recorded_once(env):
    uid, test, pay = env
    answers = good_answers(test, 25)
    res = exam_events.process(uid, test, "full", ev(test, "submit", answers, "n1", submitted=True), pay)
    assert res["reveal"] and res["toast"] and pay["revealed"]
    att = db.list_attempts(uid)
    assert len(att) == 1 and att[0]["score"] == scoring.score_scope(test, answers)["score"] != 40
    # nộp lại (hoặc autosave muộn) không tạo thêm lượt và không ghi đè
    exam_events.process(uid, test, "full", ev(test, "submit", {"1": "x"}, "n2", submitted=True), pay)
    exam_events.process(uid, test, "full", ev(test, "autosave", {}, "n3"), pay)
    assert len(db.list_attempts(uid)) == 1
    assert db.get_progress(uid, test["id"])["submitted"] is True


def test_exit_right_after_submit_still_counts_as_submit(env):
    """Trước đây sự kiện submit bị 'exit' ghi đè -> bài quay về 'đang làm' và mất kết quả."""
    uid, test, pay = env
    answers = good_answers(test, 30)
    res = exam_events.process(uid, test, "full", ev(test, "exit", answers, "n1", submitted=True), pay)
    assert res["event"] == "exit" and not res["reveal"]
    assert len(db.list_attempts(uid)) == 1
    assert db.get_progress(uid, test["id"])["submitted"] is True


def test_blank_submit_is_saved_but_not_counted(env):
    uid, test, pay = env
    exam_events.process(uid, test, "full", ev(test, "submit", {}, "n1", submitted=True), pay)
    assert db.list_attempts(uid) == [] and db.get_progress(uid, test["id"])["submitted"] is True


def test_reset_clears_progress_and_hides_answers(env):
    uid, test, pay = env
    exam_events.process(uid, test, "full", ev(test, "submit", good_answers(test, 5), "n1", submitted=True), pay)
    assert pay["revealed"]
    exam_events.process(uid, test, "full", ev(test, "reset", {}, "n2"), pay)
    assert db.get_progress(uid, test["id"]) is None and pay["revealed"] is False
    exam_events.process(uid, test, "full", ev(test, "autosave", {"1": "TRUE"}, "n3"), pay)       # làm lại được bình thường
    assert db.get_progress(uid, test["id"])["submitted"] is False


def test_prefs_written_only_when_changed_and_dark_defaults_to_none(env):
    uid, test, pay = env
    p = {"darkMode": None, "fontSize": 15, "split": 42}
    exam_events.process(uid, test, "full", ev(test, "autosave", {}, "n1", prefs=p), pay)
    assert db.get_prefs(uid)["darkMode"] is None
    db.save_prefs(uid, {"sentinel": 1})
    exam_events.process(uid, test, "full", ev(test, "autosave", {}, "n2", prefs=p), pay)         # không đổi -> không ghi lại
    assert db.get_prefs(uid) == {"sentinel": 1}
    exam_events.process(uid, test, "full", ev(test, "autosave", {}, "n3", prefs={**p, "darkMode": True}), pay)
    assert db.get_prefs(uid)["darkMode"] is True


def test_cancel_and_foreign_events(env):
    uid, test, pay = env
    assert exam_events.process(uid, test, "full", ev(test, "cancel", {}, "n1"), pay)["event"] == "cancel"
    assert db.get_progress(uid, test["id"]) is None
    other = ev(test, "autosave", {"1": "x"}, "n2"); other["testId"] = "khac"
    assert exam_events.process(uid, test, "full", other, pay) is None
    wrong_scope = ev(test, "autosave", {"1": "x"}, "n3"); wrong_scope["scope"] = "p2"
    assert exam_events.process(uid, test, "full", wrong_scope, pay) is None
    assert exam_events.process(uid, test, "full", None, pay) is None


# ------------------------------------------------------------------------- scoring/catalog
def test_public_test_hides_answers_until_reveal(env):
    _, test, _ = env
    pub = scoring.public_test(test)
    assert "answers" not in pub and "pairQuestions" not in pub and pub["passages"] == test["passages"]
    assert scoring.reveal_payload(test, {"1": "x"})["answers"] == test["answers"]


def test_clean_state_keeps_ts_and_clean_prefs_dark_none(env):
    _, test, _ = env
    assert scoring.clean_state(test, {"ts": 123456789012}, "full")["ts"] == 123456789012
    assert scoring.clean_state(test, {"ts": -5}, "full")["ts"] == 0
    assert scoring.clean_prefs({"darkMode": "yes", "fontSize": 99, "split": "x"}) == {"darkMode": None, "fontSize": 22, "split": 42}


def test_load_explanations(tmp_path, monkeypatch):
    assert catalog.load_explanations("band-4-5-education-test-1")["1"]
    assert catalog.load_explanations("../../etc/passwd") == {} and catalog.load_explanations("khong-co-de-nay") == {}


def test_write_catalog_survives_read_only_disk(monkeypatch):
    def boom(*a, **k):
        raise OSError("read-only")
    monkeypatch.setattr(Path, "write_text", boom)
    assert catalog.write_catalog()["categories"]
