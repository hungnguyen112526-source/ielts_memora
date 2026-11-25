import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import scoring  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data/reading/orange/orange-21"


def load(n):
    return json.loads((DATA / f"test-{n}.json").read_text(encoding="utf-8"))


def perfect(test):
    return {q: v[0] for q, v in test["answers"].items()}


def test_normalize():
    assert scoring.normalize("Mining.") == "mining"
    assert scoring.normalize("  Well-Being ") == scoring.normalize("well being")
    assert scoring.normalize("“x”") == "x"


def test_full_and_passage_scores():
    t = load(3)
    ans = perfect(t)
    r = scoring.score_scope(t, ans, "full")
    assert (r["score"], r["total"], r["band"]) == (40, 40, "9.0")
    r2 = scoring.score_scope(t, ans, "p2")
    assert (r2["score"], r2["total"], r2["band"], r2["scope"]) == (13, 13, None, "p2")
    assert len(r2["byPassage"]) == 1
    only_p1 = {k: v for k, v in ans.items() if 1 <= int(k) <= 13}
    assert scoring.score_scope(t, only_p1, "p1")["score"] == 13
    assert scoring.score_scope(t, only_p1, "full")["score"] == 13


def test_bad_scope_falls_back_to_full():
    t = load(3)
    assert scoring.parse_scope(t, "p9") == ("full", None)
    assert scoring.parse_scope(t, "../x") == ("full", None)


def test_pair_questions_any_order():
    t = load(2)
    a, b, valid = t["pairQuestions"][0]
    assert scoring.is_correct(t, {str(a): valid[1], str(b): valid[0]}, a)
    assert scoring.is_correct(t, {str(a): valid[1], str(b): valid[0]}, b)
    assert not scoring.is_correct(t, {str(a): valid[0], str(b): valid[0]}, b)


def test_clean_state_limits_answers_to_scope():
    t = load(3)
    st = scoring.clean_state(t, {"answers": {"1": "a", "20": "b"}, "limit": 600, "spent": 99999, "passage": 2}, "p1")
    assert st["answers"] == {"1": "a"}
    assert st["spent"] == 600 and st["passage"] == 0 and st["scope"] == "p1"
    assert scoring.answered_count(t, {"1": "a", "20": "b"}, "p1") == 1


def test_clean_state_keeps_question_highlights():
    t = load(3)
    hl = {"0": [{"s": 1, "e": 5, "c": "yellow"}], "q1": [{"s": 2, "e": 9, "c": "red"}],
          "q9": [{"s": 0, "e": 3, "c": "red"}], "qx": [], "1": [{"s": 4, "e": 2, "c": "red"}]}
    st = scoring.clean_state(t, {"hl": hl}, "full")
    assert st["hl"] == {"0": [{"s": 1, "e": 5, "c": "yellow"}], "q1": [{"s": 2, "e": 9, "c": "red"}], "1": []}
    st = scoring.clean_state(t, {"hl": hl}, "p2")
    assert set(st["hl"]) == {"q1", "1"}
