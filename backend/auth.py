"""用户认证与多用户会话管理。"""
from __future__ import annotations

import re
import secrets
import time
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from db import require_db
from settings import get_setting, set_setting

ALLOW_REGISTRATION_KEY = "allow_registration"
USERNAME_PATTERN = re.compile(r"^[\w\u4e00-\u9fa5\-_]{2,30}$")
TOKEN_EXPIRY_DAYS = 30


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)


def has_users() -> bool:
    conn = require_db()
    row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    return bool(row and row["cnt"] > 0)


def is_registration_allowed() -> bool:
    val = get_setting(ALLOW_REGISTRATION_KEY, "1")
    return val in ("1", "true", "True", "yes", "on")


def set_registration_allowed(allowed: bool | str | int) -> None:
    val = "1" if str(allowed).lower() in ("1", "true", "yes", "on") else "0"
    set_setting(ALLOW_REGISTRATION_KEY, val)


def user_to_dict(row: Any) -> dict:
    if not row:
        return {}
    d = dict(row)
    d.pop("password_hash", None)
    return d


def get_user_by_id(user_id: int) -> dict | None:
    conn = require_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return user_to_dict(row) if row else None


def get_user_by_username(username: str) -> dict | None:
    conn = require_db()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    return dict(row) if row else None


def create_user(
    username: str,
    password: str,
    nickname: str = "",
    role: str = "user",
) -> tuple[dict | None, str]:
    username = username.strip()
    nickname = (nickname or username).strip()

    if not USERNAME_PATTERN.match(username):
        return None, "用户名需为 2~30 位字符（支持中英文、数字、下划线及减号）"
    if not password or len(password) < 6:
        return None, "密码长度不能少于 6 位"

    conn = require_db()
    # 检查是否为系统中首个用户
    cnt_row = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
    is_first = not cnt_row or cnt_row["cnt"] == 0
    if is_first:
        role = "admin"
    else:
        if not is_registration_allowed():
            return None, "系统当前已关闭新用户注册，请联系管理员"

    existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    if existing:
        return None, "用户名已被注册，请尝试其他用户名"

    now = int(time.time() * 1000)
    p_hash = hash_password(password)

    cur = conn.execute(
        "INSERT INTO users (username, password_hash, role, nickname, create_time) VALUES (?, ?, ?, ?, ?)",
        (username, p_hash, role, nickname, now),
    )
    user_id = cur.lastrowid
    conn.commit()

    user = get_user_by_id(user_id)
    return user, ""


def authenticate(username: str, password: str) -> tuple[dict | None, str]:
    username = username.strip()
    if not username or not password:
        return None, "用户名和密码不能为空"

    user_row = get_user_by_username(username)
    if not user_row:
        return None, "用户名或密码错误"

    if not verify_password(password, user_row["password_hash"]):
        return None, "用户名或密码错误"

    return user_to_dict(user_row), ""


def create_token(user_id: int, days: int = TOKEN_EXPIRY_DAYS) -> str:
    token = secrets.token_hex(32)
    now = int(time.time())
    expire = now + days * 86400

    conn = require_db()
    # 顺便清理已过期令牌
    conn.execute("DELETE FROM user_tokens WHERE expire_time < ?", (now,))
    conn.execute(
        "INSERT INTO user_tokens (token, user_id, create_time, expire_time) VALUES (?, ?, ?, ?)",
        (token, user_id, now, expire),
    )
    conn.commit()
    return token


def verify_token(token: str) -> dict | None:
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    now = int(time.time())

    conn = require_db()
    row = conn.execute(
        """
        SELECT u.id, u.username, u.role, u.nickname, u.create_time
        FROM user_tokens t
        JOIN users u ON t.user_id = u.id
        WHERE t.token = ? AND t.expire_time > ?
        """,
        (token, now),
    ).fetchone()

    return user_to_dict(row) if row else None


def revoke_token(token: str) -> None:
    if not token:
        return
    conn = require_db()
    conn.execute("DELETE FROM user_tokens WHERE token=?", (token.strip(),))
    conn.commit()


def revoke_all_user_tokens(user_id: int) -> None:
    conn = require_db()
    conn.execute("DELETE FROM user_tokens WHERE user_id=?", (user_id,))
    conn.commit()


def change_password(user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
    if not new_password or len(new_password) < 6:
        return False, "新密码长度不能少于 6 位"

    conn = require_db()
    row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        return False, "用户不存在"

    if not verify_password(old_password, row["password_hash"]):
        return False, "原密码不正确"

    new_hash = hash_password(new_password)
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
    # 密码修改后注销其余 token
    conn.commit()
    return True, "密码修改成功"


def list_users() -> list[dict]:
    conn = require_db()
    rows = conn.execute(
        "SELECT id, username, role, nickname, create_time FROM users ORDER BY id ASC"
    ).fetchall()
    return [dict(r) for r in rows]


def delete_user(target_user_id: int, current_user_id: int) -> tuple[bool, str]:
    if target_user_id == current_user_id:
        return False, "不能删除当前登录的账号"

    conn = require_db()
    row = conn.execute("SELECT role FROM users WHERE id=?", (target_user_id,)).fetchone()
    if not row:
        return False, "用户不存在"

    # 删除用户相关数据（书籍、令牌等）
    conn.execute("DELETE FROM users WHERE id=?", (target_user_id,))
    conn.execute("DELETE FROM book WHERE user_id=?", (target_user_id,))
    conn.commit()
    return True, "用户删除成功"


def update_user_role(target_user_id: int, new_role: str, current_user_id: int) -> tuple[bool, str]:
    if new_role not in ("admin", "user"):
        return False, "角色不合法"
    if target_user_id == current_user_id and new_role != "admin":
        return False, "不能取消自己的管理员权限"

    conn = require_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, target_user_id))
    conn.commit()
    return True, "角色更新成功"
