"""应用设置（key-value 存储 + 代理、超时与并发线程数配置）。

设置存于 settings 表：
- proxy: 代理地址，如 http://127.0.0.1:7890
- timeout: 爬虫与搜索单源请求超时时间（秒，默认 15）
- max_workers: 多源并发检索最大线程数（默认 12）
"""
from __future__ import annotations

import re
from db import require_db

PROXY_KEY = "proxy"
PROXY_ENABLED_KEY = "proxy_enabled"
M_TO_WWW_KEY = "m_to_www"
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


def get_m_to_www() -> bool:
    """是否开启移动端网址自动转换为桌面端 (m. -> www.) 开关。"""
    v = get_setting(M_TO_WWW_KEY, "0")
    return v in ("1", "true", "True", "yes", "on")


def set_m_to_www(enabled: bool | str | int) -> None:
    val = "1" if str(enabled).lower() in ("1", "true", "yes", "on") else "0"
    set_setting(M_TO_WWW_KEY, val)


def convert_m_to_www(url: str) -> str:
    """将网址中的移动端域名前缀 m. 转换为 www."""
    if not url or not isinstance(url, str):
        return url
    # 匹配 http://m. 或 https://m. 或 //m.
    new_url = re.sub(r"^(https?://|//)m\.", r"\1www.", url, flags=re.IGNORECASE)
    if new_url != url:
        return new_url
    # 匹配不带协议的域名 m.xxx.com
    if re.match(r"^m\.[a-zA-Z0-9-]+\.[a-zA-Z]+", url, flags=re.IGNORECASE):
        return re.sub(r"^m\.", r"www.", url, flags=re.IGNORECASE)
    return url


def convert_www_to_m(url: str) -> str:
    """将网址中的桌面端域名前缀 www. 转换为 m."""
    if not url or not isinstance(url, str):
        return url
    new_url = re.sub(r"^(https?://|//)www\.", r"\1m.", url, flags=re.IGNORECASE)
    if new_url != url:
        return new_url
    if re.match(r"^www\.[a-zA-Z0-9-]+\.[a-zA-Z]+", url, flags=re.IGNORECASE):
        return re.sub(r"^www\.", r"m.", url, flags=re.IGNORECASE)
    return url


def normalize_source_url(url: str) -> str:
    """根据系统设置对源 URL 进行规范化处理（若开启 m_to_www 则自动转为 www.）。"""
    if not url or not isinstance(url, str):
        return url
    if get_m_to_www():
        return convert_m_to_www(url)
    return url


def get_raw_proxy() -> str:
    """获取数据库中保存的代理地址字符串（不论是否开启开关）。"""
    return (get_setting(PROXY_KEY) or "").strip()


def get_proxy_enabled() -> bool:
    """是否启用了网络代理总开关。"""
    v = get_setting(PROXY_ENABLED_KEY, "")
    if not v:
        # 未显式配置开关时：若已有代理地址则默认开启，否则关闭
        return bool(get_raw_proxy())
    return v in ("1", "true", "True", "yes", "on")


def set_proxy_enabled(enabled: bool | str | int) -> None:
    val = "1" if str(enabled).lower() in ("1", "true", "yes", "on") else "0"
    set_setting(PROXY_ENABLED_KEY, val)


def get_proxy() -> str:
    """当前生效的 HTTP 代理地址。若代理总开关未开启，则返回空字符串（直连）。"""
    if not get_proxy_enabled():
        return ""
    return get_raw_proxy()


def set_proxy(proxy: str) -> None:
    set_setting(PROXY_KEY, (proxy or "").strip())


def test_proxy_connection(proxy_url: str = "") -> dict:
    """探测代理连通性、响应延迟与外部出口 IP。"""
    import json
    import time
    from curl_cffi import requests as cffi_requests

    t0 = time.perf_counter()
    proxy = (proxy_url or get_raw_proxy() or "").strip()
    if not proxy:
        return {"ok": False, "error": "代理地址为空，请输入代理 URL", "delay": -1}

    targets = [
        "https://api.ipify.org?format=json",
        "https://httpbin.org/ip",
        "https://www.cloudflare.com/cdn-cgi/trace",
        "https://www.baidu.com",
    ]

    last_err = None
    for target in targets:
        try:
            resp = cffi_requests.get(
                target,
                impersonate="chrome120",
                timeout=10,
                proxy=proxy,
                verify=False,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            )
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            if resp.status_code < 400:
                body = resp.text.strip()
                out_ip = ""
                try:
                    out_ip = json.loads(body).get("ip") or json.loads(body).get("origin")
                except Exception:
                    for line in body.splitlines():
                        if line.startswith("ip="):
                            out_ip = line.split("=", 1)[1].strip()

                return {
                    "ok": True,
                    "delay": elapsed_ms,
                    "status": resp.status_code,
                    "ip": out_ip or "已正常连接",
                    "proxy": proxy,
                }
        except Exception as e:
            last_err = e

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    return {
        "ok": False,
        "delay": elapsed_ms,
        "error": str(last_err) if last_err else "代理无法连通",
        "proxy": proxy,
    }


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


HEALTH_CHECK_ENABLED_KEY = "health_check_enabled"
HEALTH_CHECK_INTERVAL_KEY = "health_check_interval"
AUTO_DISABLE_DEAD_KEY = "auto_disable_dead"


def get_health_check_enabled() -> bool:
    v = get_setting(HEALTH_CHECK_ENABLED_KEY, "1")
    return v in ("1", "true", "True")


def set_health_check_enabled(enabled: bool | str | int) -> None:
    val = "1" if str(enabled).lower() in ("1", "true") else "0"
    set_setting(HEALTH_CHECK_ENABLED_KEY, val)


def get_health_check_interval() -> int:
    """巡检周期（小时，默认 6 小时）。"""
    v = get_setting(HEALTH_CHECK_INTERVAL_KEY, "6")
    try:
        return max(1, min(48, int(v)))
    except ValueError:
        return 6


def set_health_check_interval(hours: int | str) -> None:
    try:
        val = max(1, min(48, int(hours)))
    except (ValueError, TypeError):
        val = 6
    set_setting(HEALTH_CHECK_INTERVAL_KEY, str(val))


def get_auto_disable_dead() -> bool:
    """是否在巡检完毕后自动禁用失效书源。"""
    v = get_setting(AUTO_DISABLE_DEAD_KEY, "0")
    return v in ("1", "true", "True")


def set_auto_disable_dead(enabled: bool | str | int) -> None:
    val = "1" if str(enabled).lower() in ("1", "true") else "0"
    set_setting(AUTO_DISABLE_DEAD_KEY, val)


AUTO_REFRESH_CHAPTERS_ENABLED_KEY = "auto_refresh_chapters_enabled"
AUTO_REFRESH_CHAPTERS_INTERVAL_KEY = "auto_refresh_chapters_interval"


def get_auto_refresh_chapters_enabled() -> bool:
    """是否启用书架内网络书籍章节列表定时自动刷新。"""
    v = get_setting(AUTO_REFRESH_CHAPTERS_ENABLED_KEY, "1")
    return v in ("1", "true", "True", "yes", "on")


def set_auto_refresh_chapters_enabled(enabled: bool | str | int) -> None:
    val = "1" if str(enabled).lower() in ("1", "true", "yes", "on") else "0"
    set_setting(AUTO_REFRESH_CHAPTERS_ENABLED_KEY, val)


def get_auto_refresh_chapters_interval() -> float:
    """书架章节定时刷新周期（小时，默认 6 小时，支持 0.5 小时等）。"""
    v = get_setting(AUTO_REFRESH_CHAPTERS_INTERVAL_KEY, "6")
    try:
        val = float(v)
        return max(0.25, min(72.0, val))
    except (ValueError, TypeError):
        return 6.0


def set_auto_refresh_chapters_interval(hours: float | int | str) -> None:
    try:
        val = max(0.25, min(72.0, float(hours)))
    except (ValueError, TypeError):
        val = 6.0
    set_setting(AUTO_REFRESH_CHAPTERS_INTERVAL_KEY, str(val))