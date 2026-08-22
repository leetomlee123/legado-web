"""书架章节定时自动刷新引擎：后台周期性自动巡检书架中所有网络书籍的目录与最新章节。

功能特性：
1. 定时调度：按用户在设置页配置的周期（0.5h/1h/2h/6h/12h/24h）在后台静默轮询。
2. 增量更新：自动比对章节数，保留已缓存的章节正文内容，发现最新章节时自动给书籍打上 `has_update=1` 更新标记。
3. 手动触发与实时进度：支持在设置页或书架一键点击「立即刷新书架」，提供实时进度（已同步 x/y 本，新增章节数等）。
4. 异常隔离：单个书源报错或网络波动不中断整体书架的批量刷新。
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from db import require_db
from logger import get_logger
from settings import (
    get_auto_refresh_chapters_enabled,
    get_auto_refresh_chapters_interval,
)
from source import refresh_web_chapters

logger = get_logger("bookshelf_refresh")


class BookshelfRefreshManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._is_running = False
        self._timer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # 实时运行状态与进度
        self._refreshing = False
        self._last_refresh_time = ""
        self._last_refresh_timestamp = 0.0
        self._progress = {
            "total": 0,
            "completed": 0,
            "currentBook": "",
            "updatedBooks": 0,
            "newChaptersTotal": 0,
            "failedBooks": 0,
        }
        self._last_result = {
            "total": 0,
            "updatedBooks": 0,
            "newChaptersTotal": 0,
            "failedBooks": 0,
            "updatedBookNames": [],
            "durationMs": 0,
        }

    def start(self) -> None:
        """启动后台定时调度线程。"""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._stop_event.clear()
            self._timer_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True,
                name="BookshelfRefreshScheduler",
            )
            self._timer_thread.start()
            logger.info(
                "书架章节定时刷新调度器已启动（刷新周期: %.1f 小时）",
                get_auto_refresh_chapters_interval(),
            )

    def stop(self) -> None:
        """停止后台调度。"""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            self._stop_event.set()

    def _scheduler_loop(self) -> None:
        """后台轮询定时调度循环。"""
        # 启动后稍作等待（20秒），避免抢占服务端初始冷启动
        if self._stop_event.wait(20):
            return

        while not self._stop_event.is_set():
            try:
                enabled = get_auto_refresh_chapters_enabled()
                interval_hours = get_auto_refresh_chapters_interval()
                interval_secs = interval_hours * 3600.0

                now = time.time()
                # 如果已开启且距离上次更新超过设定周期，触发静默更新
                if enabled and (now - self._last_refresh_timestamp >= interval_secs):
                    self.run_refresh(manual=False)
            except Exception as e:
                logger.error("书架章节定时刷新调度循环异常: %s", e)

            # 每隔 30 秒检查一次配置与时间
            if self._stop_event.wait(30):
                break

    def run_refresh(self, manual: bool = False) -> dict[str, Any]:
        """执行书架内所有网络书籍的章节列表刷新。"""
        with self._lock:
            if self._refreshing:
                return self.get_status()
            self._refreshing = True
            self._progress = {
                "total": 0,
                "completed": 0,
                "currentBook": "正在检索书架书籍...",
                "updatedBooks": 0,
                "newChaptersTotal": 0,
                "failedBooks": 0,
            }

        logger.info("开始执行书架书籍章节刷新（%s）...", "手动触发" if manual else "定时后台自动")
        t0 = time.perf_counter()

        try:
            conn = require_db()
            rows = conn.execute(
                "SELECT id, uuid, name, author, source_id, source_url, source_type, book_group, in_bookcase "
                "FROM book WHERE source_type='web' AND in_bookcase=1 ORDER BY id DESC"
            ).fetchall()
            books = [dict(r) for r in rows]
            total_books = len(books)

            if total_books == 0:
                logger.info("书架内无网络书籍，跳过章节刷新")
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                with self._lock:
                    self._refreshing = False
                    self._last_refresh_time = now_str
                    self._last_refresh_timestamp = time.time()
                    self._progress["total"] = 0
                    self._progress["completed"] = 0
                    self._progress["currentBook"] = ""
                return self.get_status()

            with self._lock:
                self._progress["total"] = total_books

            updated_books_count = 0
            new_chapters_total = 0
            failed_books_count = 0
            updated_names = []

            # 控制适度并发（3 个线程并发，既高效又避免对目标书源造成高频冲击）
            workers = min(3, total_books)

            def _refresh_single_book(b_info: dict) -> tuple[dict, int, Exception | None]:
                b_name = b_info.get("name") or "未知书籍"
                try:
                    added_count = refresh_web_chapters(b_info)
                    return b_info, added_count, None
                except Exception as ex:
                    return b_info, 0, ex

            with ThreadPoolExecutor(max_workers=workers) as executor:
                future_to_book = {executor.submit(_refresh_single_book, b): b for b in books}
                for f in as_completed(future_to_book):
                    b_info, added_count, err = f.result()
                    b_name = b_info.get("name") or ""

                    with self._lock:
                        self._progress["completed"] += 1
                        self._progress["currentBook"] = b_name

                    if err is not None:
                        failed_books_count += 1
                        with self._lock:
                            self._progress["failedBooks"] = failed_books_count
                        logger.warning("刷新《%s》章节失败: %s", b_name, err)
                    else:
                        if added_count > 0:
                            updated_books_count += 1
                            new_chapters_total += added_count
                            updated_names.append(f"{b_name} (+{added_count}章)")
                            with self._lock:
                                self._progress["updatedBooks"] = updated_books_count
                                self._progress["newChaptersTotal"] = new_chapters_total

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")

            with self._lock:
                self._refreshing = False
                self._last_refresh_time = now_str
                self._last_refresh_timestamp = time.time()
                self._last_result = {
                    "total": total_books,
                    "updatedBooks": updated_books_count,
                    "newChaptersTotal": new_chapters_total,
                    "failedBooks": failed_books_count,
                    "updatedBookNames": updated_names,
                    "durationMs": elapsed_ms,
                }
                self._progress["currentBook"] = ""

            logger.info(
                "书架章节刷新完成（耗时 %dms）：共检测 %d 本书，%d 本书发现共 %d 个新章节，%d 本失败",
                elapsed_ms,
                total_books,
                updated_books_count,
                new_chapters_total,
                failed_books_count,
            )

        except Exception as e:
            logger.error("书架章节刷新任务异常: %s", e)
            with self._lock:
                self._refreshing = False
                self._progress["currentBook"] = ""

        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        """获取当前书架章节刷新状态、配置与上次结果。"""
        with self._lock:
            return {
                "refreshing": self._refreshing,
                "enabled": get_auto_refresh_chapters_enabled(),
                "intervalHours": get_auto_refresh_chapters_interval(),
                "lastRefreshTime": self._last_refresh_time,
                "progress": dict(self._progress),
                "lastResult": dict(self._last_result),
            }


# 单例管理实例
bookshelf_refresh_manager = BookshelfRefreshManager()
