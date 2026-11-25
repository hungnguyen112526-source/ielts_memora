"""Server-side scoring. Mirrors the rules in engine/reader/index.html so the
score we store never depends on what the browser reports."""
from __future__ import annotations

DEFAULT_BANDS = [(39, "9.0"), (37, "8.5"), (35, "8.0"), (33, "7.5"), (30, "7.0"), (27, "6.5"),
                 (23, "6.0"), (19, "5.5"), (15, "5.0"), (13, "4.5"), (10, "4.0"), (8, "3.5"),
                 (6, "3.0"), (4, "2.5")]


def normalize(value) -> str:
    return " ".join(str("" if value is None else value).strip().lower().split())


def is_correct(test: dict, answers: dict, q: int) -> bool:
    user = normalize(answers.get(str(q)))
    if not user:
        return False
    for a, b, valid in test.get("pairQuestions", []):
        if q in (a, b):
            valid_lower = [v.lower() for v in valid]
            u1, u2 = normalize(answers.get(str(a))), normalize(answers.get(str(b)))
            return u1 in valid_lower if q == a else (u2 in valid_lower and u2 != u1)
    return user in [normalize(x) for x in test["answers"][str(q)]]


def band_for(test: dict, score: int) -> str:
    table = test.get("bandTable") or DEFAULT_BANDS
    for minimum, band in table:
        if score >= minimum:
            return band
    return "2.0"


def score_test(test: dict, answers: dict) -> dict:
    by_passage = []
    for i, p in enumerate(test["passages"], 1):
        lo, hi = p["qRange"]
        correct = sum(is_correct(test, answers, q) for q in range(lo, hi + 1))
        by_passage.append({"label": f"Passage {i}", "correct": correct, "total": hi - lo + 1})
    score = sum(p["correct"] for p in by_passage)
    return {"score": score, "total": test["totalQuestions"], "band": band_for(test, score),
            "byPassage": by_passage}


HL_COLORS = ("yellow", "orange", "red")
MAX_LIMIT_SEC = 180 * 60
MAX_HL_PER_PASSAGE = 300


def _int(v, lo: int, hi: int, default: int) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return default
    return min(hi, max(lo, int(v)))


def _clean_highlights(raw, n_passages: int) -> dict:
    """{passage: [{s, e, c}]}: vùng ký tự đã highlight, chỉ giữ dữ liệu hợp lệ."""
    out: dict[str, list] = {}
    if not isinstance(raw, dict):
        return out
    for k, items in raw.items():
        if not str(k).isdigit() or int(k) >= n_passages or not isinstance(items, list):
            continue
        clean = []
        for h in items[:MAX_HL_PER_PASSAGE]:
            if not isinstance(h, dict) or h.get("c") not in HL_COLORS:
                continue
            s, e = _int(h.get("s"), 0, 10_000_000, -1), _int(h.get("e"), 0, 10_000_000, -1)
            if 0 <= s < e:
                clean.append({"s": s, "e": e, "c": h["c"]})
        out[str(int(k))] = clean
    return out


def clean_state(test: dict, state: dict | None) -> dict:
    """Validate the state object sent by the browser before it is stored."""
    state = state if isinstance(state, dict) else {}
    total = test["totalQuestions"]
    n_pass = len(test["passages"])
    answers = {}
    raw = state.get("answers") if isinstance(state.get("answers"), dict) else {}
    for k, v in raw.items():
        if str(k).isdigit() and 1 <= int(k) <= total and isinstance(v, str):
            answers[str(int(k))] = v[:200]

    mode = "passage" if state.get("mode") == "passage" else "full"
    default_limit = int(test.get("durationMin", 60)) * 60
    limit = _int(state.get("limit"), 0, MAX_LIMIT_SEC, default_limit)      # 0 = không giới hạn
    cap = limit if limit > 0 else 24 * 3600
    spent = _int(state.get("spent"), 0, cap, 0)
    pspent, pdone = {}, {}
    if isinstance(state.get("pspent"), dict):
        for k, v in state["pspent"].items():
            if str(k).isdigit() and int(k) < n_pass:
                pspent[str(int(k))] = _int(v, 0, cap, 0)
    if isinstance(state.get("pdone"), dict):
        for k, v in state["pdone"].items():
            if str(k).isdigit() and int(k) < n_pass and v:
                pdone[str(int(k))] = True
    return {
        "answers": answers, "submitted": bool(state.get("submitted")),
        "score": state.get("score") if isinstance(state.get("score"), int) else None,
        "configured": bool(state.get("configured")), "mode": mode, "limit": limit,
        "spent": spent, "pspent": pspent, "pdone": pdone,
        "passage": _int(state.get("passage"), 0, max(0, n_pass - 1), 0),
        "hl": _clean_highlights(state.get("hl"), n_pass),
    }


def all_passages_done(test: dict, state: dict) -> bool:
    return state.get("mode") != "passage" or all(str(i) in state.get("pdone", {}) for i in range(len(test["passages"])))


def spent_seconds(state: dict) -> int:
    """Tổng thời gian đã làm: chế độ từng passage thì cộng thời gian của các passage."""
    if state.get("mode") == "passage":
        return sum(int(v) for v in (state.get("pspent") or {}).values())
    return int(state.get("spent") or 0)
