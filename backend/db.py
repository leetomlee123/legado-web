"""SQLite 连接与数据目录。"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

db: sqlite3.Connection | None = None

_HERE = Path(__file__).resolve().parent


def data_dir() -> Path:
    env = os.environ.get("LEGADO_DATA")
    if env:
        return Path(env).resolve()

    candidates = [
        _HERE.parent / "data",
        _HERE / "data",
        Path("data").resolve(),
        Path("backend") / "data",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return (_HERE.parent / "data").resolve()


def upload_dir() -> Path:
    return data_dir() / "uploads"


import threading

_local = threading.local()


def open_db() -> sqlite3.Connection:
    global db
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    upload_dir().mkdir(parents=True, exist_ok=True)

    path = d / "legado.db"
    conn = sqlite3.connect(str(path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    schema = (_HERE / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)

    # 自动迁移检查（向旧数据库补充 uuid, in_bookcase 字段）
    try:
        cols = [c[1] for c in conn.execute("PRAGMA table_info(book)").fetchall()]
        if "uuid" not in cols:
            conn.execute("ALTER TABLE book ADD COLUMN uuid TEXT DEFAULT ''")
        if "in_bookcase" not in cols:
            conn.execute("ALTER TABLE book ADD COLUMN in_bookcase INTEGER DEFAULT 1")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_book_uuid ON book (uuid) WHERE uuid != ''")
        conn.commit()
    except Exception as e:
        print(f"[db] migration error: {e}")

    print(f"sqlite: {path}")
    db = conn
    return conn


def require_db() -> sqlite3.Connection:
    if hasattr(_local, "conn") and _local.conn is not None:
        return _local.conn
    path = data_dir() / "legado.db"
    conn = sqlite3.connect(str(path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    _local.conn = conn
    return conn
