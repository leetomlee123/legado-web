"""PostgreSQL 数据库引擎集成测试。"""
import os
import pytest
from urllib.parse import urlparse

import auth
from db import close_db, is_postgres, open_db, require_db
from main import app

PG_TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://user_85BFkr:password_6ymXXK@127.0.0.1:5432/user_85BFkr",
)


def is_pg_available() -> bool:
    try:
        import psycopg2
        conn = psycopg2.connect(PG_TEST_URL, connect_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_pg_available(),
    reason="PostgreSQL 测试实例不可用，跳过 PG 专门测试",
)


@pytest.fixture(autouse=True)
def setup_pg(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", PG_TEST_URL)
    close_db()
    open_db()

    conn = require_db()
    # 清空测试数据表
    conn.execute("DELETE FROM user_tokens")
    conn.execute("DELETE FROM chapter")
    conn.execute("DELETE FROM read_progress")
    conn.execute("DELETE FROM history")
    conn.execute("DELETE FROM book")
    conn.execute("DELETE FROM users")
    conn.execute("DELETE FROM settings")
    conn.commit()

    yield

    close_db()


def test_pg_engine_detection():
    assert is_postgres() is True


def test_pg_user_creation_and_auth():
    # 1. 第一个用户为超级管理员
    admin, err = auth.create_user("pg_admin", "adminpass", "PG管理员")
    assert not err
    assert admin is not None
    assert admin["role"] == "admin"
    assert admin["id"] > 0

    # 2. 第二个用户为读者
    user2, err = auth.create_user("pg_reader", "readerpass", "PG读者")
    assert not err
    assert user2 is not None
    assert user2["role"] == "user"
    assert user2["id"] > admin["id"]

    # 3. 密码验证
    auth_ok, _ = auth.authenticate("pg_admin", "adminpass")
    assert auth_ok is not None
    assert auth_ok["username"] == "pg_admin"

    # 4. Token 签发与验证
    token = auth.create_token(admin["id"])
    verified = auth.verify_token(token)
    assert verified is not None
    assert verified["id"] == admin["id"]


def test_pg_settings_upsert():
    from settings import get_setting, set_setting

    set_setting("test_key", "val_1")
    assert get_setting("test_key") == "val_1"

    # ON CONFLICT 更新
    set_setting("test_key", "val_2")
    assert get_setting("test_key") == "val_2"


def test_pg_book_crud_and_isolation():
    client = app.test_client()

    # 注册用户 A
    resp_a = client.post("/api/auth/register", json={"username": "pg_user_a", "password": "passwordA"})
    token_a = resp_a.get_json()["token"]

    # 注册用户 B
    resp_b = client.post("/api/auth/register", json={"username": "pg_user_b", "password": "passwordB"})
    token_b = resp_b.get_json()["token"]

    # 用户 A 添加网络书籍
    resp = client.post(
        "/api/books/init-preview",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "name": "PG独家测试书籍",
            "bookUrl": "http://example.com/pg_book",
            "sourceId": 1,
            "inBookcase": True,
        },
    )
    assert resp.status_code == 200
    book_a = resp.get_json()
    assert book_a["id"] > 0
    assert book_a["name"] == "PG独家测试书籍"

    # 用户 A 书架查出 1 本
    resp = client.get("/api/books", headers={"Authorization": f"Bearer {token_a}"})
    items_a = resp.get_json()["items"]
    assert len(items_a) == 1

    # 用户 B 书架为 0 本（数据隔离）
    resp = client.get("/api/books", headers={"Authorization": f"Bearer {token_b}"})
    items_b = resp.get_json()["items"]
    assert len(items_b) == 0

    # 用户 B 尝试访问用户 A 的书籍 -> 404
    resp = client.get(f"/api/books/{book_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
