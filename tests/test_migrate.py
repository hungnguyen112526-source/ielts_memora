import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_legacy_passage_mode_is_converted(tmp_path, monkeypatch):
    monkeypatch.setenv("MEMORA_DB", str(tmp_path / "t.db"))
    from core import db, migrate
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    db.init_db()
    with db.connect() as c:
        c.execute("INSERT INTO users(username,display_name,pw_salt,pw_hash,pw_iters,created_at) VALUES('u','U','s','h',1,1)")
    legacy = {"answers": {"1": "x", "2": "y", "20": "z"}, "submitted": False, "configured": True, "mode": "passage",
              "limit": 1200, "spent": 0, "pspent": {"0": 300, "1": 100}, "pdone": {"0": True}, "passage": 1, "hl": {}}
    db.save_progress(1, "orange-21-test-3", legacy)
    assert migrate.run() == 1
    full = db.get_progress(1, "orange-21-test-3")
    assert "pdone" not in full and "mode" not in full
    assert full["spent"] == 400 and full["limit"] == 3600 and full["scope"] == "full"
    p1 = db.get_progress(1, db.pkey("orange-21-test-3", "p1"))
    assert p1["submitted"] and p1["answers"] == {"1": "x", "2": "y"}
    att = db.list_attempts(1)
    assert len(att) == 1 and att[0]["scope"] == "p1" and att[0]["valid"]
    assert migrate.run() == 0          # chạy lại không đổi gì
