"""Check every Reading test file before it goes into the app.

    python tools/validate.py            # all tests
    python tools/validate.py path.json  # one file

Exit code 1 if any problem is found.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "reading"
PLACEHOLDER = re.compile(r"\{\{(\d+)\}\}")
KNOWN_TYPES = {"tfng", "mcq", "multi2", "matching", "notes", "summary_box",
               "summary_text", "table", "flowchart"}


def referenced_questions(node, out: set[int]) -> None:
    """Collect every question number a group draws (q fields, qPair, {{n}} placeholders)."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "q" and isinstance(v, int):
                out.add(v)
            elif k == "qPair" and isinstance(v, list):
                out.update(x for x in v if isinstance(x, int))
            else:
                referenced_questions(v, out)
    elif isinstance(node, list):
        for v in node:
            referenced_questions(v, out)
    elif isinstance(node, str):
        out.update(int(m) for m in PLACEHOLDER.findall(node))


def validate_test(path: Path, seen_ids: set[str]) -> list[str]:
    errs: list[str] = []
    try:
        t = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"JSON không hợp lệ: {e}"]

    for key in ("id", "series", "category", "title", "durationMin", "totalQuestions", "passages", "answers"):
        if key not in t:
            errs.append(f"thiếu trường '{key}'")
    if errs:
        return errs

    if t["id"] in seen_ids:
        errs.append(f"id trùng: {t['id']}")
    seen_ids.add(t["id"])

    parts = path.relative_to(DATA).parts
    if len(parts) == 3:
        if t["category"] != parts[0]:
            errs.append(f"category '{t['category']}' không khớp thư mục '{parts[0]}'")
        if t["series"] != parts[1]:
            errs.append(f"series '{t['series']}' không khớp thư mục '{parts[1]}'")

    total = t["totalQuestions"]
    answers = t["answers"]
    expected = {str(i) for i in range(1, total + 1)}
    if set(answers) != expected:
        missing = sorted(expected - set(answers), key=int)
        extra = sorted(set(answers) - expected, key=int)
        if missing: errs.append(f"thiếu đáp án câu: {missing}")
        if extra:   errs.append(f"đáp án thừa (ngoài 1–{total}): {extra}")
    for q, a in answers.items():
        if not isinstance(a, list) or not a or any(not isinstance(x, str) or not x.strip() for x in a):
            errs.append(f"đáp án câu {q} phải là danh sách chuỗi không rỗng")

    prev_end = 0
    for i, p in enumerate(t["passages"], 1):
        where = f"passage {i}"
        for key in ("label", "title", "paragraphs", "groups", "qRange"):
            if key not in p:
                errs.append(f"{where}: thiếu '{key}'")
        if "qRange" not in p or "groups" not in p:
            continue
        lo, hi = p["qRange"]
        if lo != prev_end + 1:
            errs.append(f"{where}: qRange bắt đầu {lo}, mong đợi {prev_end + 1}")
        prev_end = hi
        refs: set[int] = set()
        for g in p["groups"]:
            if g.get("type") not in KNOWN_TYPES:
                errs.append(f"{where}: dạng câu hỏi lạ '{g.get('type')}' ({g.get('title')})")
            referenced_questions(g, refs)
        want = set(range(lo, hi + 1))
        if refs != want:
            if want - refs: errs.append(f"{where}: câu không có trong đề: {sorted(want - refs)}")
            if refs - want: errs.append(f"{where}: câu nằm ngoài {lo}–{hi}: {sorted(refs - want)}")
    if prev_end != total:
        errs.append(f"các passage kết thúc ở câu {prev_end}, nhưng totalQuestions = {total}")

    for entry in t.get("pairQuestions", []):
        *qs, _valid = entry
        for x in qs:
            if str(x) not in answers:
                errs.append(f"pairQuestions {qs} không có đáp án câu {x}")
    return errs


def main(argv: list[str]) -> int:
    files = [Path(a).resolve() for a in argv] or sorted(DATA.rglob("test-*.json"))
    seen: set[str] = set()
    bad = 0
    for f in files:
        errs = validate_test(f, seen)
        label = f.relative_to(DATA).as_posix()
        if errs:
            bad += 1
            print(f"✗ {label}")
            for e in errs:
                print(f"    - {e}")
        else:
            print(f"✓ {label}")
    print(f"\n{len(files) - bad}/{len(files)} đề hợp lệ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
