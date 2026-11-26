"""Đăng ký / đăng nhập / tiến độ trên SQLite, và trên PostgreSQL nếu đặt TEST_DATABASE_URL."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PG = os.environ.get("TEST_DATABASE_URL")
BACKENDS = ["sqlite"] + (["postgres"] if PG else [])


@pytest.fixture(params=BACKENDS)
def store(request, tmp_path, monkeypatch):
    from core import db
    monkeypatch.setenv("MEMORA_DB", str(tmp_path / "t.db"))
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    if request.param == "postgres":
        monkeypatch.setenv("DATABASE_URL", PG)
        db.init_db()
        with db.connect() as c:
            c.execute("TRUNCATE users, sessions, login_attempts, reading_progress, reading_attempts, user_prefs RESTART IDENTITY CASCADE")
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        db.init_db()
    return db


def test_register_login_progress(store):
    from core import auth
    ok, _, uid = auth.register("Phihung", "Hung", "matkhau123", "matkhau123")
    assert ok and uid
    ok, msg, _ = auth.register("phihung", "Dup", "matkhau123", "matkhau123")      # trùng, không phân biệt hoa thường
    assert not ok and "đã có" in msg
    ok, _, user = auth.authenticate("PHIHUNG", "matkhau123")
    assert ok and user["id"] == uid
    ok, _, _ = auth.authenticate("phihung", "sai-mat-khau")
    assert not ok

    store.save_progress(uid, "t1", {"answers": {"1": "a"}, "submitted": False})
    store.save_progress(uid, "t1", {"answers": {"1": "b"}, "submitted": True})    # ghi đè (upsert)
    assert store.get_progress(uid, "t1")["answers"] == {"1": "b"}
    assert store.progress_summary(uid)["t1"]["submitted"] is True
    store.add_attempt(uid, "t1", 30, 40, "7.0", 1800, {"answered": 40})
    att = store.list_attempts(uid)
    assert len(att) == 1 and att[0]["valid"] and att[0]["band"] == "7.0"
    store.save_prefs(uid, {"darkMode": True})
    assert store.get_prefs(uid) == {"darkMode": True}

    token = auth.create_session(uid)
    assert auth.user_from_token(token)["username"] == "Phihung"
    assert len(auth.list_users()) == 1
    assert store.export_all()["users"][0]["username"] == "Phihung"
    auth.delete_user(uid)
    assert store.get_progress(uid, "t1") is None                                  # xóa kéo theo dữ liệu liên quan


def test_lockout(store):
    from core import auth
    auth.register("bob_x", "Bob", "matkhau123", "matkhau123")
    for _ in range(auth.MAX_FAILS):
        auth.authenticate("BOB_X", "sai")
    ok, msg, _ = auth.authenticate("bob_x", "matkhau123")
    assert not ok and "quá nhiều" in msg
