"""SQLite storage: users, login sessions, login attempts, reading progress."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("MEMORA_DB", Path(__file__).resolve().parent.parent / "memora.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name  TEXT NOT NULL,
    pw_salt       TEXT NOT NULL,
    pw_hash       TEXT NOT NULL,
    pw_iters      INTEGER NOT NULL,
    created_at    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  INTEGER NOT NULL,
    expires_at  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    username  TEXT NOT NULL COLLATE NOCASE,
    ts        INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts ON login_attempts(username, ts);

-- Current state of each test for each user (resume where you left off).
CREATE TABLE IF NOT EXISTS reading_progress (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_id     TEXT NOT NULL,
    state_json  TEXT NOT NULL,
    submitted   INTEGER NOT NULL DEFAULT 0,
    updated_at  INTEGER NOT NULL,
    PRIMARY KEY (user_id, test_id)
);

-- One row per submitted attempt (feeds the dashboard).
CREATE TABLE IF NOT EXISTS reading_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_id     TEXT NOT NULL,
    score       INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    band        TEXT NOT NULL,
    seconds     INTEGER NOT NULL,
    detail_json TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON reading_attempts(user_id, created_at);

CREATE TABLE IF NOT EXISTS user_prefs (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    prefs_json TEXT NOT NULL
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as c:
        c.executescript(SCHEMA)
        # Nâng cấp DB cũ: thêm cột trạng thái tài khoản (active / blocked)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
        if "status" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")


def now() -> int:
    return int(time.time())


# ---------------------------------------------------------------- progress
def get_progress(user_id: int, test_id: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT state_json FROM reading_progress WHERE user_id=? AND test_id=?",
            (user_id, test_id),
        ).fetchone()
    return json.loads(row["state_json"]) if row else None


def save_progress(user_id: int, test_id: str, state: dict) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO reading_progress(user_id, test_id, state_json, submitted, updated_at)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id, test_id) DO UPDATE SET
                 state_json=excluded.state_json,
                 submitted=excluded.submitted,
                 updated_at=excluded.updated_at""",
            (user_id, test_id, json.dumps(state, ensure_ascii=False),
             1 if state.get("submitted") else 0, now()),
        )


def delete_progress(user_id: int, test_id: str) -> None:
    with connect() as c:
        c.execute("DELETE FROM reading_progress WHERE user_id=? AND test_id=?", (user_id, test_id))


def progress_summary(user_id: int) -> dict[str, dict]:
    """test_id -> {submitted, answered, updated_at} (cheap, for library cards)."""
    with connect() as c:
        rows = c.execute(
            "SELECT test_id, state_json, submitted, updated_at FROM reading_progress WHERE user_id=?",
            (user_id,),
        ).fetchall()
    out = {}
    for r in rows:
        st = json.loads(r["state_json"])
        answers = st.get("answers") or {}
        out[r["test_id"]] = {
            "submitted": bool(r["submitted"]),
            "answered": sum(1 for v in answers.values() if str(v).strip()),
            "updated_at": r["updated_at"],
            "mode": st.get("mode"),
            "pdone": len(st.get("pdone") or {}),
        }
    return out


def add_attempt(user_id: int, test_id: str, score: int, total: int, band: str,
                seconds: int, detail: dict) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO reading_attempts(user_id,test_id,score,total,band,seconds,detail_json,created_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (user_id, test_id, score, total, band, seconds,
             json.dumps(detail, ensure_ascii=False), now()),
        )


def list_attempts(user_id: int, limit: int = 200) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            """SELECT id,test_id,score,total,band,seconds,detail_json,created_at
               FROM reading_attempts WHERE user_id=? ORDER BY created_at DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------- prefs
def get_prefs(user_id: int) -> dict:
    with connect() as c:
        row = c.execute("SELECT prefs_json FROM user_prefs WHERE user_id=?", (user_id,)).fetchone()
    return json.loads(row["prefs_json"]) if row else {}


def save_prefs(user_id: int, prefs: dict) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO user_prefs(user_id, prefs_json) VALUES(?,?)
               ON CONFLICT(user_id) DO UPDATE SET prefs_json=excluded.prefs_json""",
            (user_id, json.dumps(prefs)),
        )
