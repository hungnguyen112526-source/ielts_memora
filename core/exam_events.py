"""Xử lý sự kiện engine làm bài gửi về (thuần Python, không dùng Streamlit nên test được).

Điểm luôn được chấm lại ở server từ đáp án người dùng gửi lên, không tin điểm do trình duyệt báo."""
from __future__ import annotations

from . import db, scoring

AUTOSAVE_EVENTS = ("autosave", "exit", "prev", "next")


def process(uid: int, test: dict, scope: str, val, pay: dict) -> dict | None:
    """Ghi DB theo sự kiện. `pay` là dữ liệu của lần mở đề (có nonce, prefs, revealed, saved) và được cập nhật tại chỗ.

    Trả về None nếu bỏ qua sự kiện, hoặc dict {"event": ..., "toast": (nội dung, icon) | None, "reveal": bool}."""
    if not isinstance(val, dict) or val.get("testId") != test["id"]:
        return None
    if scoring.parse_scope(test, val.get("scope"))[0] != scope:
        return None                                         # event của lần mở trước (phạm vi khác)
    nonce = val.get("nonce")
    if not nonce or pay.get("nonce") == nonce:
        return None                                         # đã xử lý (Streamlit chạy lại sẽ gửi lại event cũ)
    pay["nonce"] = nonce

    event = val.get("event")
    out = {"event": event, "toast": None, "reveal": False}
    if event == "cancel":                                   # thoát khỏi hộp thiết lập, chưa bắt đầu làm
        return out

    tid, pk = test["id"], db.pkey(test["id"], scope)
    state = scoring.clean_state(test, val.get("state"), scope)

    prefs = val.get("prefs")
    if isinstance(prefs, dict):
        new_prefs = scoring.clean_prefs(prefs)
        if new_prefs != pay.get("prefs"):                   # chỉ ghi DB khi cài đặt thật sự đổi
            db.save_prefs(uid, new_prefs)
            pay["prefs"] = new_prefs

    # Trình duyệt báo "đã nộp" nhưng sự kiện submit bị sự kiện sau (thoát, chuyển đề, autosave) ghi đè -> vẫn chấm như nộp bài
    client_done = bool((val.get("state") or {}).get("submitted"))
    submit = event == "submit" or (event in AUTOSAVE_EVENTS and client_done)

    if event == "reset":
        db.delete_progress(uid, pk)
        pay["saved"], pay["revealed"] = None, False
    elif submit:
        result = scoring.score_scope(test, state["answers"], scope)
        state.update(submitted=True, score=result["score"])
        wrote = db.save_progress_if_open(uid, pk, state)    # False = bài này đã nộp từ trước: không ghi đè, không tính lượt mới
        pay["revealed"] = True
        out["reveal"] = event == "submit"
        if wrote:
            answered = scoring.answered_count(test, state["answers"], scope)
            if answered:                                    # lượt trắng không tính vào thống kê
                timeout = bool((val.get("result") or {}).get("timeout"))
                db.add_attempt(uid, tid, result["score"], result["total"], result["band"], state["spent"],
                               {"byPassage": result["byPassage"], "timeout": timeout, "answered": answered,
                                "answers": state["answers"]}, scope=scope)
            label = (f"Band {result['band']} ({result['score']}/{result['total']})" if result["band"]
                     else f"{result['score']}/{result['total']} câu đúng")
            out["toast"] = (f"Đã nộp bài · {label}", "✅")
    elif event in AUTOSAVE_EVENTS:
        state["submitted"] = False
        db.save_progress_if_open(uid, pk, state)            # không bao giờ ghi đè bài đã nộp
    return out
