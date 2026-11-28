"""Accounts and login sessions. Pure Python (no Streamlit) so it is easy to test."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from . import db

PBKDF2_ITERS = 310_000
SESSION_DAYS = 14
MAX_FAILS = 5            # failed logins allowed ...
FAIL_WINDOW_SEC = 600    # ... within this window (per username)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,30}$")


# ----------------------------------------------------------------- hashing
def _hash(password: str, salt: bytes, iters: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# -------------------------------------------------------------- validation
def validate_registration(username: str, display_name: str, password: str, confirm: str) -> str | None:
    """Return an error message (Vietnamese) or None if everything is valid."""
    if not USERNAME_RE.match(username or ""):
        return "Tên đăng nhập gồm 3–30 ký tự: chữ cái, số, dấu gạch dưới hoặc dấu chấm."
    if not (1 <= len((display_name or "").strip()) <= 50):
        return "Tên hiển thị không được để trống và tối đa 50 ký tự."
    if len(password or "") < 8:
        return "Mật khẩu cần ít nhất 8 ký tự."
    if len(password) > 128:
        return "Mật khẩu tối đa 128 ký tự."
    if password.lower() == username.lower():
        return "Mật khẩu không được trùng với tên đăng nhập."
    if password != confirm:
        return "Mật khẩu nhập lại không khớp."
    return None


# ---------------------------------------------------------------- register
def register(username: str, display_name: str, password: str, confirm: str) -> tuple[bool, str, int | None]:
    err = validate_registration(username, display_name, password, confirm)
    if err:
        return False, err, None
    salt = secrets.token_bytes(16)
    try:
        with db.connect() as c:
            new_id = c.insert_id(
                "INSERT INTO users(username, display_name, pw_salt, pw_hash, pw_iters, created_at) VALUES(?,?,?,?,?,?)",
                (username, display_name.strip(), salt.hex(), _hash(password, salt, PBKDF2_ITERS),
                 PBKDF2_ITERS, db.now()),
            )
            return True, "Tạo tài khoản thành công.", new_id
    except db.IntegrityError:
        return False, "Tên đăng nhập này đã có người dùng.", None


# ------------------------------------------------------------ authenticate
def _recent_failures(c, username: str) -> int:
    since = db.now() - FAIL_WINDOW_SEC
    return c.execute(
        "SELECT COUNT(*) FROM login_attempts WHERE lower(username)=lower(?) AND ts>=?", (username, since)
    ).fetchone()[0]


def authenticate(username: str, password: str) -> tuple[bool, str, dict | None]:
    username = (username or "").strip()
    with db.connect() as c:
        if _recent_failures(c, username) >= MAX_FAILS:
            return False, "Đăng nhập sai quá nhiều lần. Vui lòng thử lại sau 10 phút.", None

        row = c.execute("SELECT * FROM users WHERE lower(username)=lower(?)", (username,)).fetchone()
        if row is None:
            # Burn the same CPU time so response time does not reveal whether the user exists.
            _hash(password or "", b"\x00" * 16, PBKDF2_ITERS)
            ok = False
        else:
            computed = _hash(password or "", bytes.fromhex(row["pw_salt"]), row["pw_iters"])
            ok = hmac.compare_digest(computed, row["pw_hash"])

        if not ok:
            c.execute("INSERT INTO login_attempts(username, ts) VALUES(?,?)", (username, db.now()))
            return False, "Sai tên đăng nhập hoặc mật khẩu.", None

        if row["status"] == "blocked":
            return False, "Tài khoản này đã bị khóa. Hãy liên hệ quản trị viên.", None

        c.execute("DELETE FROM login_attempts WHERE lower(username)=lower(?)", (username,))
        return True, "OK", {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}


# ---------------------------------------------------------------- sessions
def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = db.now()
    with db.connect() as c:
        c.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        c.execute(
            "INSERT INTO sessions(token_hash, user_id, created_at, expires_at) VALUES(?,?,?,?)",
            (_token_hash(token), user_id, now, now + SESSION_DAYS * 86400),
        )
    return token


def user_from_token(token: str | None) -> dict | None:
    if not token:
        return None
    with db.connect() as c:
        row = c.execute(
            """SELECT u.id, u.username, u.display_name
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash=? AND s.expires_at >= ? AND u.status = 'active'""",
            (_token_hash(token), db.now()),
        ).fetchone()
    return dict(row) if row else None


def is_active(user_id: int) -> bool:
    """Tài khoản còn tồn tại và chưa bị khóa."""
    with db.connect() as c:
        row = c.execute("SELECT status FROM users WHERE id=?", (user_id,)).fetchone()
    return bool(row) and row["status"] == "active"


def delete_session(token: str | None) -> None:
    if not token:
        return
    with db.connect() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (_token_hash(token),))


def change_password(user_id: int, old: str, new: str, confirm: str) -> tuple[bool, str]:
    with db.connect() as c:
        row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if row is None:
            return False, "Không tìm thấy tài khoản."
        if not hmac.compare_digest(_hash(old, bytes.fromhex(row["pw_salt"]), row["pw_iters"]), row["pw_hash"]):
            return False, "Mật khẩu hiện tại không đúng."
        err = validate_registration(row["username"], row["display_name"], new, confirm)
        if err:
            return False, err
        salt = secrets.token_bytes(16)
        c.execute(
            "UPDATE users SET pw_salt=?, pw_hash=?, pw_iters=? WHERE id=?",
            (salt.hex(), _hash(new, salt, PBKDF2_ITERS), PBKDF2_ITERS, user_id),
        )
        c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))  # sign out everywhere
    return True, "Đã đổi mật khẩu. Các thiết bị khác sẽ phải đăng nhập lại."


# ------------------------------------------------------------------- admin
def is_admin(username: str, admin_names) -> bool:
    """Quản trị viên = tên đăng nhập nằm trong danh sách khai báo ở Secrets / biến môi trường."""
    names = {str(n).strip().lower() for n in (admin_names or []) if str(n).strip()}
    return (username or "").lower() in names


def list_users() -> list[dict]:
    with db.connect() as c:
        rows = c.execute(
            """SELECT u.id, u.username, u.display_name, u.status, u.created_at,
                      (SELECT COUNT(*) FROM reading_attempts a WHERE a.user_id = u.id) AS attempts,
                      (SELECT MAX(created_at) FROM reading_attempts a WHERE a.user_id = u.id) AS last_attempt
               FROM users u ORDER BY u.created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def set_status(user_id: int, status: str) -> tuple[bool, str]:
    if status not in ("active", "blocked"):
        return False, "Trạng thái không hợp lệ."
    with db.connect() as c:
        c.execute("UPDATE users SET status=? WHERE id=?", (status, user_id))
        if status == "blocked":
            c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    return True, "Đã khóa tài khoản." if status == "blocked" else "Đã mở khóa tài khoản."


def admin_reset_password(user_id: int, new: str) -> tuple[bool, str]:
    if len(new or "") < 8 or len(new) > 128:
        return False, "Mật khẩu mới cần từ 8 đến 128 ký tự."
    salt = secrets.token_bytes(16)
    with db.connect() as c:
        c.execute("UPDATE users SET pw_salt=?, pw_hash=?, pw_iters=? WHERE id=?",
                  (salt.hex(), _hash(new, salt, PBKDF2_ITERS), PBKDF2_ITERS, user_id))
        c.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM login_attempts WHERE lower(username)=(SELECT lower(username) FROM users WHERE id=?)", (user_id,))
    return True, "Đã đặt lại mật khẩu. Người dùng sẽ phải đăng nhập lại."


def delete_user(user_id: int) -> tuple[bool, str]:
    with db.connect() as c:
        c.execute("DELETE FROM users WHERE id=?", (user_id,))     # bảng liên quan tự xóa theo (ON DELETE CASCADE)
    return True, "Đã xóa tài khoản và toàn bộ dữ liệu của người đó."
