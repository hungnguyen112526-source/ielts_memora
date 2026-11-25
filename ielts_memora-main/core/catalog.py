"""Library index for Reading tests.

Layout on disk:
    data/reading/categories.json
    data/reading/<category>/<series>/series.json
    data/reading/<category>/<series>/test-<n>.json

`catalog.json` is a light index (no passage text). It is rebuilt automatically
whenever a source file is newer than it, so adding a test is just dropping a file in.
Test content is only read when a test is opened.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "reading"
CATALOG_PATH = DATA_DIR / "catalog.json"

_NUM_RE = re.compile(r"(\d+)")


def _natural_key(name: str):
    return [int(p) if p.isdigit() else p for p in _NUM_RE.split(name)]


def _sources() -> list[Path]:
    return [p for p in DATA_DIR.rglob("*.json") if p.name != "catalog.json"]


def _signature() -> int:
    """Changes when any source file is added, removed or modified."""
    parts = sorted(f"{p.relative_to(DATA_DIR).as_posix()}:{p.stat().st_mtime_ns}:{p.stat().st_size}"
                   for p in _sources())
    return int(hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12], 16)


def build_catalog() -> dict:
    cats_cfg = json.loads((DATA_DIR / "categories.json").read_text(encoding="utf-8"))["categories"]
    categories = []
    for cfg in sorted(cats_cfg, key=lambda c: c.get("order", 99)):
        cat = {**cfg, "series": []}
        cat_dir = DATA_DIR / cfg["id"]
        if cat_dir.is_dir():
            for s_dir in sorted((d for d in cat_dir.iterdir() if d.is_dir()), key=lambda d: _natural_key(d.name)):
                s_file = s_dir / "series.json"
                if not s_file.exists():
                    continue
                series = json.loads(s_file.read_text(encoding="utf-8"))
                tests = []
                for t_file in sorted(s_dir.glob("test-*.json"), key=lambda p: _natural_key(p.name)):
                    t = json.loads(t_file.read_text(encoding="utf-8"))
                    tests.append({
                        "id": t["id"],
                        "file": t_file.relative_to(DATA_DIR).as_posix(),
                        "title": t["title"],
                        "summary": t.get("summary", ""),
                        "module": t.get("module", "academic"),
                        "durationMin": t.get("durationMin", 60),
                        "totalQuestions": t["totalQuestions"],
                        "questionTypes": t.get("questionTypes", []),
                        "passages": [p["title"] for p in t["passages"]],
                    })
                series["tests"] = tests
                cat["series"].append(series)
            cat["series"].sort(key=lambda s: s.get("order", 99))
        categories.append(cat)
    return {"generated": int(time.time()), "signature": _signature(), "categories": categories}


def write_catalog() -> dict:
    cat = build_catalog()
    CATALOG_PATH.write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
    return cat


def load_catalog() -> dict:
    """Return the catalog, rebuilding it first if any source file changed."""
    if CATALOG_PATH.exists():
        try:
            cat = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
            if cat.get("signature") == _signature():
                return cat
        except (json.JSONDecodeError, OSError):
            pass
    return write_catalog()


def find_test_entry(catalog: dict, test_id: str) -> dict | None:
    for cat in catalog["categories"]:
        for series in cat["series"]:
            for t in series["tests"]:
                if t["id"] == test_id:
                    return {**t, "category": cat["id"], "series_id": series["id"], "series_title": series["title"]}
    return None


def load_test(catalog: dict, test_id: str) -> dict | None:
    """Read one full test. The path always comes from the catalog, never from user input."""
    entry = find_test_entry(catalog, test_id)
    if entry is None:
        return None
    return json.loads((DATA_DIR / entry["file"]).read_text(encoding="utf-8"))


def neighbours(catalog: dict, test_id: str) -> tuple[str | None, str | None]:
    """(previous_test_id, next_test_id) inside the same series."""
    for cat in catalog["categories"]:
        for series in cat["series"]:
            ids = [t["id"] for t in series["tests"]]
            if test_id in ids:
                i = ids.index(test_id)
                return (ids[i - 1] if i > 0 else None, ids[i + 1] if i < len(ids) - 1 else None)
    return None, None
