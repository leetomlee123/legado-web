"""数据库连接与数据目录（支持 SQLite 与 PostgreSQL 双引擎）。"""
from __future__ import annotations

import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlparse

_HERE = Path(__file__).resolve().parent
_local = threading.local()

TABLES_WITH_ID = {"users", "book", "chapter", "book_source", "read_progress", "history"}


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


def get_database_url() -> str:
    """获取数据库连接 URL。优先读取 DATABASE_URL / POSTGRES_URL，或 PG_* / POSTGRES_* 环境变量。"""
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""
    if url:
        return url.strip()

    pg_host = os.environ.get("PG_HOST") or os.environ.get("POSTGRES_HOST") or ""
    if pg_host:
        pg_port = os.environ.get("PG_PORT") or os.environ.get("POSTGRES_PORT") or "5432"
        pg_user = os.environ.get("PG_USER") or os.environ.get("POSTGRES_USER") or "postgres"
        pg_password = os.environ.get("PG_PASSWORD") or os.environ.get("POSTGRES_PASSWORD") or ""
        pg_db = os.environ.get("PG_DATABASE") or os.environ.get("POSTGRES_DB") or "legado"
        auth_part = f"{pg_user}:{pg_password}@" if pg_password else f"{pg_user}@"
        return f"postgresql://{auth_part}{pg_host}:{pg_port}/{pg_db}"

    return ""


def is_postgres() -> bool:
    url = get_database_url()
    return url.startswith("postgresql://") or url.startswith("postgres://")


def convert_sql_placeholders(sql: str) -> str:
    """将 SQLite 的 ? 占位符转换为 PostgreSQL 的 %s（忽略单引号内文本）。"""
    parts = sql.split("'")
    for i in range(0, len(parts), 2):
        parts[i] = parts[i].replace("?", "%s")
    return "'".join(parts)


def prepare_pg_insert(sql: str) -> tuple[str, bool]:
    """为缺少 RETURNING 的 INSERT 语句追加 RETURNING id，以支持获取 lastrowid。"""
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()
    if sql_upper.startswith("INSERT INTO") and " RETURNING " not in sql_upper:
        m = re.match(r"^INSERT\s+INTO\s+([a-zA-Z0-9_]+)", sql_stripped, re.IGNORECASE)
        if m:
            tbl = m.group(1).lower()
            if tbl in TABLES_WITH_ID:
                return f"{sql_stripped} RETURNING id", True
    return sql_stripped, False


class PostgresCursorWrapper:
    """包装 psycopg2 cursor，使其与 sqlite3.Cursor 的 lastrowid、fetchone、fetchall 等行为一致。"""

    def __init__(self, raw_cursor):
        self._cursor = raw_cursor
        self.lastrowid = 0

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        pg_sql, added_returning = prepare_pg_insert(sql)
        pg_sql = convert_sql_placeholders(pg_sql)

        if params is not None:
            params_tuple = tuple(params) if isinstance(params, (list, tuple)) else params
            self._cursor.execute(pg_sql, params_tuple)
        else:
            self._cursor.execute(pg_sql)

        if added_returning:
            try:
                row = self._cursor.fetchone()
                if row:
                    self.lastrowid = int(row[0])
            except Exception:
                pass
        return self

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]):
        pg_sql = convert_sql_placeholders(sql)
        self._cursor.executemany(pg_sql, seq_of_params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchmany(self, size=None):
        return self._cursor.fetchmany(size)

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        try:
            self._cursor.close()
        except Exception:
            pass

    def __iter__(self):
        return iter(self._cursor)


class PostgresConnectionWrapper:
    """包装 psycopg2 Connection，统一 execute / executemany / commit / executescript 接口。"""

    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        import psycopg2.extras
        raw_cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(raw_cur)

    def execute(self, sql: str, params: Sequence[Any] | None = None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]):
        cur = self.cursor()
        cur.executemany(sql, seq_of_params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def executescript(self, script: str):
        with self._conn.cursor() as cur:
            cur.execute(script)
        self._conn.commit()


def ensure_postgres_database(url: str) -> None:
    """确保目标 PostgreSQL 数据库存在，若不存在则尝试自动创建。"""
    import psycopg2

    parsed = urlparse(url)
    target_db = parsed.path.lstrip("/")
    if not target_db:
        return

    # 优先连接目标库看是否存在
    try:
        conn = psycopg2.connect(url)
        conn.close()
        return
    except Exception:
        pass

    # 尝试连接默认的 postgres / template1 数据库进行创建
    admin_candidates = ["postgres", "template1"]
    for adm in admin_candidates:
        try:
            admin_conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                dbname=adm,
            )
            admin_conn.autocommit = True
            with admin_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
                if not cur.fetchone():
                    cur.execute(f'CREATE DATABASE "{target_db}"')
            admin_conn.close()
            return
        except Exception:
            continue


def get_pg_connection() -> PostgresConnectionWrapper:
    import psycopg2

    if hasattr(_local, "pg_conn") and _local.pg_conn is not None:
        try:
            if not _local.pg_conn._conn.closed:
                # 快速检查连接活跃状态
                _local.pg_conn._conn.isolation_level
                return _local.pg_conn
        except Exception:
            try:
                _local.pg_conn.close()
            except Exception:
                pass
            _local.pg_conn = None

    url = get_database_url()
    raw = psycopg2.connect(url)
    wrapper = PostgresConnectionWrapper(raw)
    _local.pg_conn = wrapper
    return wrapper


def open_db():
    d = data_dir()
    d.mkdir(parents=True, exist_ok=True)
    upload_dir().mkdir(parents=True, exist_ok=True)

    if is_postgres():
        url = get_database_url()
        ensure_postgres_database(url)
        conn = get_pg_connection()
        schema = (_HERE / "schema_pg.sql").read_text(encoding="utf-8")
        conn.executescript(schema)

        # 检查迁移字段
        try:
            cur = conn.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'book'")
            cols = [r[0] for r in cur.fetchall()]
            if "uuid" not in cols:
                conn.execute("ALTER TABLE book ADD COLUMN uuid VARCHAR(128) DEFAULT ''")
            if "in_bookcase" not in cols:
                conn.execute("ALTER TABLE book ADD COLUMN in_bookcase INTEGER DEFAULT 1")
            if "user_id" not in cols:
                conn.execute("ALTER TABLE book ADD COLUMN user_id INTEGER DEFAULT 1")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_book_uuid ON book (uuid) WHERE uuid != ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_book_user_shelf ON book (user_id, in_bookcase)")
            conn.commit()
        except Exception as e:
            print(f"[db pg] migration check: {e}")

        parsed = urlparse(url)
        print(f"[db] PostgreSQL connected: {parsed.hostname}:{parsed.port or 5432}/{parsed.path.lstrip('/')}")
        return conn

    # SQLite
    path = d / "legado.db"
    conn = sqlite3.connect(str(path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    # Migration check on existing tables before schema indexes run
    try:
        table_exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='book'").fetchone()
        if table_exists:
            cols = [c[1] for c in conn.execute("PRAGMA table_info(book)").fetchall()]
            if "uuid" not in cols:
                conn.execute("ALTER TABLE book ADD COLUMN uuid TEXT DEFAULT ''")
            if "in_bookcase" not in cols:
                conn.execute("ALTER TABLE book ADD COLUMN in_bookcase INTEGER DEFAULT 1")
            if "user_id" not in cols:
                conn.execute("ALTER TABLE book ADD COLUMN user_id INTEGER DEFAULT 1")
            conn.commit()
    except Exception as e:
        print(f"[db sqlite] pre-migration error: {e}")

    schema = (_HERE / "schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema)

    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_book_uuid ON book (uuid) WHERE uuid != ''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_book_user_shelf ON book (user_id, in_bookcase)")
        conn.commit()
    except Exception as e:
        print(f"[db sqlite] migration error: {e}")

    print(f"[db] SQLite connected: {path}")
    return conn


def require_db():
    if is_postgres():
        return get_pg_connection()

    if hasattr(_local, "conn") and _local.conn is not None:
        return _local.conn
    path = data_dir() / "legado.db"
    conn = sqlite3.connect(str(path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    _local.conn = conn
    return conn


def close_db():
    if is_postgres():
        if hasattr(_local, "pg_conn") and _local.pg_conn is not None:
            _local.pg_conn.close()
            _local.pg_conn = None
    else:
        if hasattr(_local, "conn") and _local.conn is not None:
            _local.conn.close()
            _local.conn = None
