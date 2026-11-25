"""Nâng cấp dữ liệu cũ: chế độ "từng passage tuần tự" đã bỏ, thay bằng phạm vi (cả đề / một passage).

Chạy một lần mỗi khi app khởi động, chạy lại nhiều lần vẫn an toàn."""
from __future__ import annotations

import json

from . import catalog as cat_mod
from . import db, scoring

LEGACY_KEYS = ("mode", "pspent", "pdone")
KEEP = ("answers", "submitted", "score", "configured", "limit", "spent", "passage", "hl")


def run() -> int:
    """Trả về số dòng đã chuyển đổi."""
    with db.connect() as c:
        rows = c.execute("SELECT user_id, test_id, state_json, submitted, updated_at FROM reading_progress").fetchall()
    catalog = cat_mod.load_catalog()
    changed = 0
    for r in rows:
        if "#" in r["test_id"]:
            continue
        st = json.loads(r["state_json"])
        if not any(k in st for k in LEGACY_KEYS):
            continue
        test = cat_mod.load_test(catalog, r["test_id"])
        pspent = st.get("pspent") or {}
        was_passage_mode = st.get("mode") == "passage"
        new = {k: st[k] for k in KEEP if k in st}
        new["scope"] = "full"
        if was_passage_mode:
            new["spent"] = sum(int(v) for v in pspent.values() if isinstance(v, (int, float)))
            if test and new.get("limit", 0) > 0:
                new["limit"] = int(test.get("durationMin", 60)) * 60      # hạn mỗi passage cũ -> hạn cả đề
        with db.connect() as c:
            if test and was_passage_mode and not r["submitted"]:
                # Passage đã nộp trong bài dở dang -> thành lượt làm lẻ riêng, giữ điểm đã có
                for idx_s in (st.get("pdone") or {}):
                    idx = int(idx_s)
                    if not (0 <= idx < len(test["passages"])):
                        continue
                    scope = f"p{idx + 1}"
                    pk = db.pkey(r["test_id"], scope)
                    if c.execute("SELECT 1 FROM reading_progress WHERE user_id=? AND test_id=?",
                                 (r["user_id"], pk)).fetchone():
                        continue
                    pstate = scoring.clean_state(test, {**st, "submitted": True, "configured": True,
                                                        "spent": pspent.get(idx_s, 0), "passage": idx}, scope)
                    res = scoring.score_scope(test, pstate["answers"], scope)
                    pstate["score"] = res["score"]
                    c.execute("INSERT INTO reading_progress(user_id,test_id,state_json,submitted,updated_at) VALUES(?,?,?,?,?)",
                              (r["user_id"], pk, json.dumps(pstate, ensure_ascii=False), 1, r["updated_at"]))
                    answered = scoring.answered_count(test, pstate["answers"], scope)
                    if answered:
                        c.execute("""INSERT INTO reading_attempts(user_id,test_id,score,total,band,seconds,detail_json,created_at,scope)
                                     VALUES(?,?,?,?,?,?,?,?,?)""",
                                  (r["user_id"], r["test_id"], res["score"], res["total"], "", pstate["spent"],
                                   json.dumps({"byPassage": res["byPassage"], "answered": answered,
                                               "migrated": True}, ensure_ascii=False),
                                   r["updated_at"], scope))
            c.execute("UPDATE reading_progress SET state_json=? WHERE user_id=? AND test_id=?",
                      (json.dumps(new, ensure_ascii=False), r["user_id"], r["test_id"]))
        changed += 1
    return changed
