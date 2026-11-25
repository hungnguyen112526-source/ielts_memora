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


def clean_state(test: dict, state: dict | None) -> dict:
    """Validate the state object sent by the browser before it is stored."""
    state = state if isinstance(state, dict) else {}
    total = test["totalQuestions"]
    answers = {}
    raw = state.get("answers") if isinstance(state.get("answers"), dict) else {}
    for k, v in raw.items():
        if str(k).isdigit() and 1 <= int(k) <= total and isinstance(v, str):
            answers[str(int(k))] = v[:200]
    limit = int(test.get("durationMin", 60)) * 60
    tl = state.get("timeLeft")
    time_left = min(limit, max(0, int(tl))) if isinstance(tl, (int, float)) else limit
    return {"answers": answers, "submitted": bool(state.get("submitted")), "timeLeft": time_left,
            "score": state.get("score") if isinstance(state.get("score"), int) else None}
