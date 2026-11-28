"""Server-side scoring. Mirrors the rules in engine/reader/index.html so the
score we store never depends on what the browser reports."""
from __future__ import annotations

import re

DEFAULT_BANDS = [(39, "9.0"), (37, "8.5"), (35, "8.0"), (33, "7.5"), (30, "7.0"), (27, "6.5"),
                 (23, "6.0"), (19, "5.5"), (15, "5.0"), (13, "4.5"), (10, "4.0"), (8, "3.5"),
                 (6, "3.0"), (4, "2.5")]


_DASH = re.compile(r"[\u2010-\u2015\u2212-]")
_EDGE = ".,;:!?\"'\u201c\u201d\u2018\u2019 "


def normalize(value) -> str:
    """Khớp với normalizeText trong engine: không phân biệt hoa/thường, gạch nối = khoảng trắng,
    bỏ dấu câu ở hai đầu ("Mining." == "mining", "well-being" == "well being")."""
    s = _DASH.sub(" ", str("" if value is None else value).lower())
    return " ".join(s.split()).strip(_EDGE)


# ------------------------------------------------------------------ phạm vi
def parse_scope(test: dict, scope) -> tuple[str, int | None]:
    """'full' (cả đề) hoặc 'p1'..'pN' (làm lẻ một passage) -> (scope chuẩn hóa, chỉ số passage hoặc None)."""
    m = re.fullmatch(r"p(\d+)", str(scope or ""))
    if m and 1 <= int(m.group(1)) <= len(test["passages"]):
        n = int(m.group(1))
        return f"p{n}", n - 1
    return "full", None


def scope_range(test: dict, scope) -> tuple[int, int]:
    _, idx = parse_scope(test, scope)
    return (1, test["totalQuestions"]) if idx is None else tuple(test["passages"][idx]["qRange"])


def is_correct(test: dict, answers: dict, q: int) -> bool:
    user = normalize(answers.get(str(q)))
    if not user:
        return False
    for entry in test.get("pairQuestions", []):
        *qs, valid = entry          # [a, b, valid] hoặc [a, b, c, valid]
        if q in qs:
            valid_norm = [normalize(v) for v in valid]
            us = [normalize(answers.get(str(x))) for x in qs]
            i = qs.index(q)
            return us[i] in valid_norm and us[i] not in us[:i]
    return user in [normalize(x) for x in test["answers"][str(q)]]


def band_for(test: dict, score: int) -> str:
    table = test.get("bandTable") or DEFAULT_BANDS
    for minimum, band in table:
        if score >= minimum:
            return band
    return "2.0"


def score_scope(test: dict, answers: dict, scope="full") -> dict:
    """Chấm cả đề hoặc một passage. Band chỉ có nghĩa khi làm đủ cả đề, passage lẻ thì band = None."""
    scope, idx = parse_scope(test, scope)
    by_passage = []
    for i, p in enumerate(test["passages"]):
        if idx is not None and i != idx:
            continue
        lo, hi = p["qRange"]
        correct = sum(is_correct(test, answers, q) for q in range(lo, hi + 1))
        by_passage.append({"label": f"Passage {i + 1}", "correct": correct, "total": hi - lo + 1})
    score = sum(p["correct"] for p in by_passage)
    total = sum(p["total"] for p in by_passage)
    return {"score": score, "total": total, "scope": scope,
            "band": band_for(test, score) if scope == "full" else None, "byPassage": by_passage}


def score_test(test: dict, answers: dict) -> dict:
    return score_scope(test, answers, "full")


def answered_count(test: dict, answers: dict, scope="full") -> int:
    lo, hi = scope_range(test, scope)
    return sum(1 for q in range(lo, hi + 1) if normalize(answers.get(str(q))))


HL_COLORS = ("yellow", "orange", "red")
MAX_LIMIT_SEC = 180 * 60
MAX_HL_PER_PASSAGE = 300


def _int(v, lo: int, hi: int, default: int) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return default
    return min(hi, max(lo, int(v)))


def _clean_highlights(raw, n_passages: int) -> dict:
    """{"0": [...], "q0": [...]}: vùng ký tự đã highlight, chỉ giữ dữ liệu hợp lệ.
    Khóa "N" là bài đọc của passage N, khóa "qN" là phần đề (câu hỏi) của passage N."""
    out: dict[str, list] = {}
    if not isinstance(raw, dict):
        return out
    for k, items in raw.items():
        ks = str(k)
        digits = ks[1:] if ks[:1] == "q" else ks
        if not digits.isdigit() or int(digits) >= n_passages or not isinstance(items, list):
            continue
        clean = []
        for h in items[:MAX_HL_PER_PASSAGE]:
            if not isinstance(h, dict) or h.get("c") not in HL_COLORS:
                continue
            s, e = _int(h.get("s"), 0, 10_000_000, -1), _int(h.get("e"), 0, 10_000_000, -1)
            if 0 <= s < e:
                clean.append({"s": s, "e": e, "c": h["c"]})
        out[("q" if ks[:1] == "q" else "") + str(int(digits))] = clean
    return out


def public_test(test: dict) -> dict:
    """Bản đề gửi xuống trình duyệt khi đang làm: KHÔNG kèm đáp án."""
    return {k: v for k, v in test.items() if k not in ("answers", "pairQuestions")}


def reveal_payload(test: dict, explanations: dict | None = None) -> dict:
    """Đáp án (và lời giải nếu có), chỉ gửi sau khi bài đã nộp."""
    return {"answers": test["answers"], "pairQuestions": test.get("pairQuestions", []),
            "explanations": explanations or {}}


def clean_prefs(prefs: dict) -> dict:
    """darkMode = None nghĩa là người dùng chưa chọn, engine sẽ theo giao diện Streamlit."""
    size, split, dark = prefs.get("fontSize"), prefs.get("split"), prefs.get("darkMode")
    return {"darkMode": dark if isinstance(dark, bool) else None,
            "fontSize": min(22, max(13, size)) if isinstance(size, (int, float)) and not isinstance(size, bool) else 15,
            "split": min(70, max(25, split)) if isinstance(split, (int, float)) and not isinstance(split, bool) else 42}


def clean_state(test: dict, state: dict | None, scope="full") -> dict:
    """Validate the state object sent by the browser before it is stored."""
    scope, pidx = parse_scope(test, scope)
    lo, hi = scope_range(test, scope)
    state = state if isinstance(state, dict) else {}
    n_pass = len(test["passages"])
    answers = {}
    raw = state.get("answers") if isinstance(state.get("answers"), dict) else {}
    for k, v in raw.items():
        if str(k).isdigit() and lo <= int(k) <= hi and isinstance(v, str):
            answers[str(int(k))] = v[:200]

    default_limit = (int(test.get("durationMin", 60)) * 60 if pidx is None
                     else round(int(test.get("durationMin", 60)) / n_pass) * 60)
    limit = _int(state.get("limit"), 0, MAX_LIMIT_SEC, default_limit)      # 0 = không giới hạn
    cap = limit if limit > 0 else 24 * 3600
    hl = _clean_highlights(state.get("hl"), n_pass)
    if pidx is not None:
        hl = {k: v for k, v in hl.items() if int(k.lstrip("q")) == pidx}
    return {
        "answers": answers, "submitted": bool(state.get("submitted")),
        "score": state.get("score") if isinstance(state.get("score"), int) else None,
        "configured": bool(state.get("configured")), "scope": scope, "limit": limit,
        "spent": _int(state.get("spent"), 0, cap, 0),
        "passage": pidx if pidx is not None else _int(state.get("passage"), 0, max(0, n_pass - 1), 0),
        "hl": hl,
        "ts": _int(state.get("ts"), 0, 10**13, 0),      # mốc thời gian (ms) của lần sửa cuối, để so với bản nháp trong trình duyệt
    }
