"""Lưu trữ: users, phiên đăng nhập, tiến độ, lịch sử làm bài.

Hai chế độ:
  * PostgreSQL (khuyên dùng khi đưa lên mạng): đặt `DATABASE_URL` trong Streamlit Secrets (hoặc biến môi trường).
    Dữ liệu nằm ở máy chủ ngoài nên KHÔNG mất khi app khởi động lại.
  * SQLite (mặc định, dùng khi chạy thử trên máy): file memora.db. Trên Streamlit Cloud ổ đĩa là tạm nên file này mất khi reboot.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

try:                                     # chỉ cần khi dùng PostgreSQL
    import psycopg
    from psycopg_pool import ConnectionPool
    IntegrityError = (sqlite3.IntegrityError, psycopg.IntegrityError)
except ImportError:                      # pragma: no cover
    psycopg = None
    ConnectionPool = None
    IntegrityError = (sqlite3.IntegrityError,)

DB_PATH = Path(os.environ.get("MEMORA_DB", Path(__file__).resolve().parent.parent / "memora.db"))


def database_url() -> str | None:
    """Chuỗi kết nối PostgreSQL từ biến môi trường hoặc Streamlit Secrets (khóa DATABASE_URL)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("DATABASE_URL")
        except Exception:
            url = None
    url = (url or "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url or None


def backend() -> str:
    return "postgres" if database_url() else "sqlite"


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
    created_at  INTEGER NOT NULL,
    scope       TEXT NOT NULL DEFAULT 'full'
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON reading_attempts(user_id, created_at);

CREATE TABLE IF NOT EXISTS user_prefs (
    user_id    INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    prefs_json TEXT NOT NULL
);
"""


SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL PRIMARY KEY,
    username      TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    pw_salt       TEXT NOT NULL,
    pw_hash       TEXT NOT NULL,
    pw_iters      INTEGER NOT NULL,
    created_at    BIGINT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active'
);
CREATE UNIQUE INDEX IF NOT EXISTS users_username_ci ON users (lower(username));

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  BIGINT NOT NULL,
    expires_at  BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id        BIGSERIAL PRIMARY KEY,
    username  TEXT NOT NULL,
    ts        BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_attempts_ci ON login_attempts (lower(username), ts);

CREATE TABLE IF NOT EXISTS reading_progress (
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_id     TEXT NOT NULL,
    state_json  TEXT NOT NULL,
    submitted   INTEGER NOT NULL DEFAULT 0,
    updated_at  BIGINT NOT NULL,
    PRIMARY KEY (user_id, test_id)
);

CREATE TABLE IF NOT EXISTS reading_attempts (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    test_id     TEXT NOT NULL,
    score       INTEGER NOT NULL,
    total       INTEGER NOT NULL,
    band        TEXT NOT NULL,
    seconds     INTEGER NOT NULL,
    detail_json TEXT NOT NULL,
    created_at  BIGINT NOT NULL,
    scope       TEXT NOT NULL DEFAULT 'full'
);
CREATE INDEX IF NOT EXISTS idx_attempts_user ON reading_attempts(user_id, created_at);

CREATE TABLE IF NOT EXISTS user_prefs (
    user_id    BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    prefs_json TEXT NOT NULL
);
"""

TABLES = ("users", "sessions", "login_attempts", "reading_progress", "reading_attempts", "user_prefs")


class Row:
    """Dòng kết quả: truy cập theo tên cột hoặc theo số, dict(row) dùng được (giống sqlite3.Row)."""
    __slots__ = ("_cols", "_vals")

    def __init__(self, cols, vals):
        self._cols, self._vals = cols, tuple(vals)

    def __getitem__(self, k):
        return self._vals[self._cols.index(k)] if isinstance(k, str) else self._vals[k]

    def keys(self):
        return list(self._cols)

    def __iter__(self):
        return iter(self._vals)

    def __len__(self):
        return len(self._vals)


def _row_factory(cursor):
    cols = [d.name for d in (cursor.description or [])]
    return lambda vals: Row(cols, vals)


class Conn:
    """Bọc kết nối để cùng một đoạn SQL (dùng dấu ?) chạy được trên cả SQLite và PostgreSQL."""

    def __init__(self, raw, pg: bool):
        self.raw, self.pg = raw, pg

    def execute(self, sql: str, params=()):
        if self.pg:
            return self.raw.execute(sql.replace("?", "%s"), params)
        return self.raw.execute(sql, params)

    def insert_id(self, sql: str, params=()) -> int:
        """INSERT một dòng và trả về id vừa tạo."""
        if self.pg:
            return self.raw.execute(sql.replace("?", "%s") + " RETURNING id", params).fetchone()[0]
        return self.raw.execute(sql, params).lastrowid


_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            if psycopg is None:
                raise RuntimeError("Thiếu thư viện psycopg. Thêm 'psycopg[binary,pool]' vào requirements.txt.")
            _pool = ConnectionPool(
                database_url(), min_size=1, max_size=6, open=True, timeout=20,
                kwargs={"row_factory": _row_factory, "prepare_threshold": None},   # prepare_threshold=None: tương thích pooler (Neon/Supabase)
                check=ConnectionPool.check_connection, max_idle=240,
            )
        return _pool


@contextmanager
def connect():
    if database_url():
        with _get_pool().connection() as raw:      # tự commit khi xong, rollback nếu lỗi
            yield Conn(raw, True)
        return
    raw = sqlite3.connect(DB_PATH, timeout=10)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    raw.execute("PRAGMA journal_mode = WAL")
    try:
        yield Conn(raw, False)
        raw.commit()
    finally:
        raw.close()


def init_db() -> None:
    if database_url():
        with connect() as c:
            c.raw.execute(SCHEMA_PG)
        return
    with connect() as c:
        c.raw.executescript(SCHEMA)
        # Nâng cấp DB cũ: thêm cột trạng thái tài khoản (active / blocked)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
        if "status" not in cols:
            c.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
        # Nâng cấp DB cũ: lượt làm có phạm vi (full = cả đề, p1..pN = một passage)
        acols = {r["name"] for r in c.execute("PRAGMA table_info(reading_attempts)")}
        if "scope" not in acols:
            c.execute("ALTER TABLE reading_attempts ADD COLUMN scope TEXT NOT NULL DEFAULT 'full'")


def export_all() -> dict:
    """Toàn bộ dữ liệu (mọi bảng) dưới dạng dict, dùng làm bản sao lưu JSON."""
    out = {}
    with connect() as c:
        for t in TABLES:
            out[t] = [dict(r) for r in c.execute(f"SELECT * FROM {t}").fetchall()]
    return out


def now() -> int:
    return int(time.time())


# ---------------------------------------------------------------- progress
def pkey(test_id: str, scope: str = "full") -> str:
    """Khóa lưu tiến độ: cả đề dùng id đề, làm lẻ một passage thêm hậu tố '#p<n>'."""
    return test_id if scope in (None, "", "full") else f"{test_id}#{scope}"


def split_key(key: str) -> tuple[str, str]:
    tid, _, scope = key.partition("#")
    return tid, scope or "full"


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
    """pkey -> {submitted, answered, updated_at} (cheap, for library cards)."""
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
        }
    return out


def add_attempt(user_id: int, test_id: str, score: int, total: int, band: str | None,
                seconds: int, detail: dict, scope: str = "full", created_at: int | None = None) -> None:
    with connect() as c:
        c.execute(
            """INSERT INTO reading_attempts(user_id,test_id,score,total,band,seconds,detail_json,created_at,scope)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (user_id, test_id, score, total, band or "", seconds,
             json.dumps(detail, ensure_ascii=False), created_at or now(), scope),
        )


def list_attempts(user_id: int, limit: int = 200) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            """SELECT id,test_id,score,total,band,seconds,detail_json,created_at,scope
               FROM reading_attempts WHERE user_id=? ORDER BY created_at DESC, id DESC LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        a = dict(r)
        detail = json.loads(a.pop("detail_json") or "{}")
        a["detail"] = detail
        # Lượt cũ chưa ghi số câu đã trả lời: coi lượt 0 điểm là lượt trắng
        answered = detail.get("answered")
        a["valid"] = (answered > 0) if isinstance(answered, int) else a["score"] > 0
        out.append(a)
    return out


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
