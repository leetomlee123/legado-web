"""应用设置（key-value 存储 + 代理配置）。

代理设置存于 settings 表：key = 'proxy'，value 形如 http://127.0.0.1:7890
为空表示不走代理。
"""
from __future__ import annotations

from db import require_db

PROXY_KEY = "proxy"


def get_setting(key: str, default: str = "") -> str:
    conn = require_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = require_db()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


def get_proxy() -> str:
    """当前配置的 HTTP 代理地址，未配置则返回空串。"""
    return (get_setting(PROXY_KEY) or "").strip()


def set_proxy(proxy: str) -> None:
    set_setting(PROXY_KEY, (proxy or "").strip())