"""书源健康度巡检引擎：后台定时/手动并发扫描书源可用性与延迟。

功能特性：
1. 定时巡检：周期性调度（1h/6h/12h/24h），静默探测所有书源并更新健康度指标。
2. 健康度分级：🟢 健康 (<=1.2s) / 🟡 迟缓 (>1.2s) / 🔴 失效 (关站/超时/TLS异常)。
3. 自动隔离机制：支持巡检后自动禁用连续失效的书源，避免拖慢全局检索。
4. 提供手动体检触发、失效源一键批量禁用与清理 API。
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from db import require_db
from logger import get_logger
from settings import (
    get_auto_disable_dead,
    get_health_check_enabled,
    get_health_check_interval,
)
from source import test_source_latency

logger = get_logger("health")


class SourceHealthManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._is_running = False
        self._timer_thread: threading.Thread | null = None
        self._stop_event = threading.Event()

        # 最近一次巡检状态与结果
        self._scanning = False
        self._last_scan_time = ""
        self._last_scan_timestamp = 0.0
        self._total = 0
        self._healthy_count = 0
        self._slow_count = 0
        self._dead_count = 0
        self._results: dict[int, dict[str, Any]] = {}

    def start(self) -> None:
        """启动后台定时扫描线程。"""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._stop_event.clear()
            self._timer_thread = threading.Thread(target=self._scheduler_loop, daemon=True, name="HealthCheckScheduler")
            self._timer_thread.start()
            logger.info("书源健康度巡检调度器已启动（巡检周期: %d 小时）", get_health_check_interval())

    def stop(self) -> None:
        """停止后台调度。"""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False
            self._stop_event.set()

    def _scheduler_loop(self) -> None:
        """后台轮询定时调度循环。"""
        # 启动后稍作等待（30秒），避免抢占服务端初始冷启动
        if self._stop_event.wait(30):
            return

        while not self._stop_event.is_set():
            try:
                enabled = get_health_check_enabled()
                interval_hours = get_health_check_interval()
                interval_secs = interval_hours * 3600

                now = time.time()
                # 如果已开启且距离上次扫描超过周期，触发扫描
                if enabled and (now - self._last_scan_timestamp >= interval_secs):
                    self.run_scan(manual=False)
            except Exception as e:
                logger.error("健康巡检调度循环发生异常: %s", e)

            # 每隔 60 秒检查一次配置与时间
            if self._stop_event.wait(60):
                break

    def run_scan(self, manual: bool = False) -> dict[str, Any]:
        """执行全量书源健康度体检。"""
        with self._lock:
            if self._scanning:
                return self.get_status()
            self._scanning = True

        logger.info("开始执行书源全面体检（%s）...", "手动触发" if manual else "定时巡检")
        start_time = time.time()

        try:
            conn = require_db()
            rows = conn.execute("SELECT id, name, url, rule, enabled FROM book_source").fetchall()
            total_sources = len(rows)

            if total_sources == 0:
                logger.info("书源库为空，跳过健康巡检")
                with self._lock:
                    self._scanning = False
                    self._total = 0
                    self._healthy_count = 0
                    self._slow_count = 0
                    self._dead_count = 0
                    self._last_scan_time = time.strftime("%Y-%m-%d %H:%M:%S")
                    self._last_scan_timestamp = time.time()
                return self.get_status()

            probe_results: dict[int, dict[str, Any]] = {}
            healthy = 0
            slow = 0
            dead = 0
            dead_ids: list[int] = []

            # 并发探测 (最大 16 线程)
            from settings import get_proxy
            active_proxy = get_proxy()
            workers = min(16, total_sources)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(
                        test_source_latency,
                        r["id"],
                        r["name"],
                        r["url"] or "",
                        r["rule"] or "",
                        timeout=8,
                        proxy=active_proxy,
                    ): r["id"]
                    for r in rows
                }
                for f in as_completed(futures):
                    sid = futures[f]
                    try:
                        res = f.result()
                    except Exception as e:
                        res = {
                            "sourceId": sid,
                            "sourceName": "",
                            "success": False,
                            "delay": -1,
                            "error": str(e),
                        }

                    # 分级归类
                    is_succ = res.get("success", False)
                    delay = res.get("delay", -1)
                    err = res.get("error")

                    if is_succ and delay >= 0:
                        if delay <= 1200:
                            category = "healthy"
                            healthy += 1
                        else:
                            category = "slow"
                            slow += 1
                    else:
                        category = "dead"
                        dead += 1
                        dead_ids.append(sid)

                    probe_results[sid] = {
                        "sourceId": sid,
                        "sourceName": res.get("sourceName", ""),
                        "category": category,
                        "delay": delay,
                        "status": res.get("status"),
                        "error": err,
                        "checkTime": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }

            elapsed = time.time() - start_time
            now_str = time.strftime("%Y-%m-%d %H:%M:%S")

            # 自动隔离机制：如果开启了 auto_disable_dead，自动将 dead 书源禁用
            auto_disable = get_auto_disable_dead()
            disabled_count = 0
            if auto_disable and dead_ids:
                placeholders = ",".join("?" for _ in dead_ids)
                conn.execute(f"UPDATE book_source SET enabled=0 WHERE id IN ({placeholders})", dead_ids)
                conn.commit()
                disabled_count = len(dead_ids)
                logger.info("自动隔离生效: 已自动将 %d 个失效书源设为禁用状态", disabled_count)

            with self._lock:
                self._scanning = False
                self._total = total_sources
                self._healthy_count = healthy
                self._slow_count = slow
                self._dead_count = dead
                self._results = probe_results
                self._last_scan_time = now_str
                self._last_scan_timestamp = time.time()

            logger.info(
                "书源体检完成（耗时 %.1fs）：共检测 %d 个源，🟢 健康 %d 个，🟡 较慢 %d 个，🔴 失效 %d 个",
                elapsed,
                total_sources,
                healthy,
                slow,
                dead,
            )

        except Exception as e:
            logger.error("书源体检执行异常: %s", e)
            with self._lock:
                self._scanning = False

        return self.get_status()

    def get_status(self) -> dict[str, Any]:
        """获取当前健康巡检汇总与详情。"""
        with self._lock:
            return {
                "scanning": self._scanning,
                "enabled": get_health_check_enabled(),
                "intervalHours": get_health_check_interval(),
                "autoDisableDead": get_auto_disable_dead(),
                "lastScanTime": self._last_scan_time,
                "total": self._total,
                "healthy": self._healthy_count,
                "slow": self._slow_count,
                "dead": self._dead_count,
                "results": self._results,
            }

    def disable_dead_sources(self) -> int:
        """手动一键禁用所有当前识别到的失效书源。"""
        with self._lock:
            dead_ids = [sid for sid, r in self._results.items() if r.get("category") == "dead"]

        if not dead_ids:
            return 0

        conn = require_db()
        placeholders = ",".join("?" for _ in dead_ids)
        conn.execute(f"UPDATE book_source SET enabled=0 WHERE id IN ({placeholders})", dead_ids)
        conn.commit()
        logger.info("已批量禁用 %d 个失效书源", len(dead_ids))
        return len(dead_ids)

    def delete_dead_sources(self) -> int:
        """手动一键删除所有当前识别到的失效书源。"""
        with self._lock:
            dead_ids = [sid for sid, r in self._results.items() if r.get("category") == "dead"]

        if not dead_ids:
            return 0

        conn = require_db()
        placeholders = ",".join("?" for _ in dead_ids)
        conn.execute(f"DELETE FROM book_source WHERE id IN ({placeholders})", dead_ids)
        conn.commit()
        with self._lock:
            for sid in dead_ids:
                self._results.pop(sid, None)
            self._dead_count = 0
            self._total = max(0, self._total - len(dead_ids))
        logger.info("已批量删除 %d 个失效书源", len(dead_ids))
        return len(dead_ids)


# 单例管理实例
health_manager = SourceHealthManager()
