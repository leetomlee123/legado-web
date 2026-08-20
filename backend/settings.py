"""应用设置（key-value 存储 + 代理、超时与并发线程数配置）。

设置存于 settings 表：
- proxy: 代理地址，如 http://127.0.0.1:7890
- timeout: 爬虫与搜索单源请求超时时间（秒，默认 15）
- max_workers: 多源并发检索最大线程数（默认 12）
"""
from __future__ import annotations

from db import require_db

PROXY_KEY = "proxy"
TIMEOUT_KEY = "timeout"
MAX_WORKERS_KEY = "max_workers"

DEFAULT_TIMEOUT = 15
DEFAULT_MAX_WORKERS = 12


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


def get_timeout() -> int:
    """搜索与爬虫请求超时时间（秒）。"""
    v = get_setting(TIMEOUT_KEY, str(DEFAULT_TIMEOUT))
    try:
        val = int(v)
        return max(1, min(120, val))
    except ValueError:
        return DEFAULT_TIMEOUT


def set_timeout(timeout: int | str) -> None:
    try:
        val = max(1, min(120, int(timeout)))
    except (ValueError, TypeError):
        val = DEFAULT_TIMEOUT
    set_setting(TIMEOUT_KEY, str(val))


def get_max_workers() -> int:
    """多源搜索并发线程数。"""
    v = get_setting(MAX_WORKERS_KEY, str(DEFAULT_MAX_WORKERS))
    try:
        val = int(v)
        return max(1, min(64, val))
    except ValueError:
        return DEFAULT_MAX_WORKERS


def set_max_workers(max_workers: int | str) -> None:
    try:
        val = max(1, min(64, int(max_workers)))
    except (ValueError, TypeError):
        val = DEFAULT_MAX_WORKERS
    set_setting(MAX_WORKERS_KEY, str(val))