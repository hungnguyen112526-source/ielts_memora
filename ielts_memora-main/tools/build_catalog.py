"""Rebuild data/reading/catalog.json (the app also does this automatically)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.catalog import write_catalog  # noqa: E402

if __name__ == "__main__":
    cat = write_catalog()
    for c in cat["categories"]:
        n = sum(len(s["tests"]) for s in c["series"])
        print(f"{c['title']:<18} {len(c['series'])} bộ, {n} đề")
