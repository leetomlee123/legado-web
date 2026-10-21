"""多用户认证与权限测试。"""
import os
import tempfile
import pytest

from db import open_db, require_db
import auth
from main import app


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    """为每个测试使用独立的临时数据库。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("LEGADO_DATA", tmpdir)
        # 重新初始化连接
        from db import _local
        if hasattr(_local, "conn") and _local.conn is not None:
            _local.conn.close()
            _local.conn = None
        open_db()
        yield


def test_first_user_is_admin():
    assert not auth.has_users()
    user, err = auth.create_user("admin", "admin123", "系统管理")
    assert not err
    assert user is not None
    assert user["username"] == "admin"
    assert user["role"] == "admin"
    assert auth.has_users()


def test_second_user_is_regular():
    admin, _ = auth.create_user("admin", "admin123", "系统管理")
    user2, err = auth.create_user("reader1", "password123", "普通读者")
    assert not err
    assert user2 is not None
    assert user2["username"] == "reader1"
    assert user2["role"] == "user"


def test_registration_toggle():
    auth.create_user("admin", "admin123")
    assert auth.is_registration_allowed()

    auth.set_registration_allowed(False)
    assert not auth.is_registration_allowed()

    # 注册被禁止
    user, err = auth.create_user("newuser", "password123")
    assert user is None
    assert "关闭" in err

    # 重新开启注册
    auth.set_registration_allowed(True)
    user, err = auth.create_user("newuser", "password123")
    assert user is not None
    assert not err


def test_authentication_and_token():
    user, _ = auth.create_user("alice", "mypassword")
    
    # 错误密码
    u_fail, err = auth.authenticate("alice", "wrongpw")
    assert u_fail is None
    assert err

    # 正确密码
    u_ok, err = auth.authenticate("alice", "mypassword")
    assert u_ok is not None
    assert u_ok["username"] == "alice"

    # Token 生成与验证
    token = auth.create_token(user["id"])
    verified_user = auth.verify_token(token)
    assert verified_user is not None
    assert verified_user["id"] == user["id"]

    # 注销 Token
    auth.revoke_token(token)
    assert auth.verify_token(token) is None


def test_change_password():
    user, _ = auth.create_user("bob", "oldpassword")
    
    ok, msg = auth.change_password(user["id"], "wrongold", "newpassword")
    assert not ok
    
    ok, msg = auth.change_password(user["id"], "oldpassword", "newpassword")
    assert ok

    u_old, _ = auth.authenticate("bob", "oldpassword")
    assert u_old is None

    u_new, _ = auth.authenticate("bob", "newpassword")
    assert u_new is not None


def test_api_auth_flow():
    client = app.test_client()

    # 1. 初始状态
    resp = client.get("/api/auth/status")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["hasUsers"] is False
    assert data["loggedIn"] is False

    # 2. 未登录访问保护路由 -> 401
    resp = client.get("/api/books")
    assert resp.status_code == 401

    # 3. 注册管理员
    resp = client.post("/api/auth/register", json={
        "username": "admin",
        "password": "adminpassword",
        "nickname": "超级管理员"
    })
    assert resp.status_code == 200
    admin_data = resp.get_json()
    admin_token = admin_data["token"]
    assert admin_data["user"]["role"] == "admin"

    # 4. 携带管理员 Token 访问书架 -> 200
    resp = client.get("/api/books", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

    # 5. 注册普通用户
    resp = client.post("/api/auth/register", json={
        "username": "reader",
        "password": "readerpassword",
        "nickname": "读者一号"
    })
    assert resp.status_code == 200
    reader_data = resp.get_json()
    reader_token = reader_data["token"]
    assert reader_data["user"]["role"] == "user"

    # 6. 普通用户访问管理员路由 -> 403
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {reader_token}"})
    assert resp.status_code == 403

    # 7. 管理员访问管理员路由 -> 200
    resp = client.get("/api/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    users_list = resp.get_json()
    assert len(users_list) == 2


def test_multi_user_bookcase_isolation():
    client = app.test_client()

    # 创建用户 A
    resp_a = client.post("/api/auth/register", json={"username": "userA", "password": "passwordA"})
    token_a = resp_a.get_json()["token"]

    # 创建用户 B
    resp_b = client.post("/api/auth/register", json={"username": "userB", "password": "passwordB"})
    token_b = resp_b.get_json()["token"]

    # 用户 A 添加书籍
    resp = client.post("/api/books/init-preview", headers={"Authorization": f"Bearer {token_a}"}, json={
        "name": "用户A的独家书",
        "bookUrl": "http://example.com/book_a",
        "sourceId": 1,
        "inBookcase": True
    })
    assert resp.status_code == 200
    book_a = resp.get_json()

    # 用户 A 可以在自己书架看到此书
    resp = client.get("/api/books", headers={"Authorization": f"Bearer {token_a}"})
    books_a = resp.get_json()["items"]
    assert len(books_a) == 1
    assert books_a[0]["name"] == "用户A的独家书"

    # 用户 B 书架应该为空
    resp = client.get("/api/books", headers={"Authorization": f"Bearer {token_b}"})
    books_b = resp.get_json()["items"]
    assert len(books_b) == 0

    # 用户 B 尝试访问用户 A 的书籍 -> 404
    resp = client.get(f"/api/books/{book_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404
