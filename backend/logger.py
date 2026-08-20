"""系统全局日志模块：支持控制台色彩输出、多级文件轮转与内存环形缓冲实时推流。

功能特性：
1. 控制台与文件滚动输出：logs/app.log (全量日志) 与 logs/error.log (错误日志)
2. 内存环形缓冲：保留最新 1000 条结构化日志供前端快速检索
3. SSE 实时推流：支持前端控制台秒级接收最新服务端日志
"""
from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from typing import Any

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

APP_LOG_FILE = os.path.join(LOGS_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "error.log")

MAX_MEMORY_LOGS = 1000
_memory_logs: deque[dict[str, Any]] = deque(maxlen=MAX_MEMORY_LOGS)
_memory_lock = threading.Lock()

# 实时推流订阅队列集合
_subscribers: set[queue.Queue] = set()
_subscribers_lock = threading.Lock()

_log_counter = 0
_counter_lock = threading.Lock()


def _next_log_id() -> int:
    global _log_counter
    with _counter_lock:
        _log_counter += 1
        return _log_counter


class InMemoryLogHandler(logging.Handler):
    """自定义日志 Handler，将日志格式化为结构化字典存入内存缓冲并通知所有实时订阅者。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))
            msecs = int(record.msecs)
            timestamp = f"{now_str}.{msecs:03d}"

            item = {
                "id": _next_log_id(),
                "time": timestamp,
                "created": record.created,
                "level": record.levelname,
                "logger": record.name,
                "message": msg,
                "module": record.module,
                "line": record.lineno,
            }

            with _memory_lock:
                _memory_logs.append(item)

            # 广播给实时 SSE 订阅客户端
            with _subscribers_lock:
                dead_subs = set()
                for q in _subscribers:
                    try:
                        q.put_nowait(item)
                    except queue.Full:
                        dead_subs.add(q)
                for q in dead_subs:
                    _subscribers.discard(q)
        except Exception:
            self.handleError(record)


# 统一格式器
STANDARD_FORMAT = "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(fmt=STANDARD_FORMAT, datefmt=DATE_FORMAT)

# 根 Logger 初始化
root_logger = logging.getLogger("legado")
root_logger.setLevel(logging.INFO)

if not root_logger.handlers:
    # 1. 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. 全量日志文件滚动 Handler (单文件 10MB，保留 5 个备份)
    app_file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_file_handler.setLevel(logging.INFO)
    app_file_handler.setFormatter(formatter)
    root_logger.addHandler(app_file_handler)

    # 3. 错误日志文件 Handler (仅 ERROR 级别，单文件 10MB，保留 5 个备份)
    err_file_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    err_file_handler.setLevel(logging.ERROR)
    err_file_handler.setFormatter(formatter)
    root_logger.addHandler(err_file_handler)

    # 4. 内存缓冲 Handler
    memory_handler = InMemoryLogHandler()
    memory_handler.setLevel(logging.INFO)
    # 简单格式化只保留消息体，其余字段在 handler 中结构化
    memory_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(memory_handler)


def get_logger(name: str = "") -> logging.Logger:
    """获取子 logger 实例。"""
    if name:
        return logging.getLogger(f"legado.{name}")
    return root_logger


def get_memory_logs(
    level: str = "",
    keyword: str = "",
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    """查询内存中的结构化日志。"""
    level = (level or "").strip().upper()
    keyword = (keyword or "").strip().lower()

    with _memory_lock:
        items = list(_memory_logs)

    # 倒序排列（最新在前）或正序
    filtered = []
    for item in items:
        if level and level != "ALL":
            if item["level"] != level:
                continue
        if keyword:
            msg = item["message"].lower()
            mod = item["module"].lower()
            if keyword not in msg and keyword not in mod:
                continue
        filtered.append(item)

    total = len(filtered)
    # 返回按时间倒序或正序，默认最新在前
    sliced = filtered[::-1][offset : offset + limit]

    return {
        "total": total,
        "items": sliced,
        "maxBuffer": MAX_MEMORY_LOGS,
    }


def clear_memory_logs() -> None:
    """清空内存中的历史日志。"""
    with _memory_lock:
        _memory_logs.clear()


def register_log_subscriber() -> queue.Queue:
    """注册新的 SSE 实时日志推流队列。"""
    q: queue.Queue = queue.Queue(maxsize=200)
    with _subscribers_lock:
        _subscribers.add(q)
    return q


def unregister_log_subscriber(q: queue.Queue) -> None:
    """注销 SSE 实时日志推流队列。"""
    with _subscribers_lock:
        _subscribers.discard(q)
