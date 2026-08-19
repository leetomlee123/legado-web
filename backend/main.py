"""Legado Web 后端（Flask + SQLite + curl_cffi）。

保持 /api 路径与 JSON 字段与原 Go 实现兼容。
网络抓取统一使用 curl_cffi impersonate=chrome120。
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory

from book import import_txt_file
from db import data_dir, open_db, require_db, upload_dir
from epub import import_epub_file
from pdf import import_pdf_file
from settings import get_proxy, set_proxy
from source import (
    crawl_book_detail,
    crawl_search,
    fetch_url,
    fetch_web_chapter,
    legado_rule_insert,
    parse_legado_rule,
    refresh_web_chapters,
    split_legado_rules,
)

MAX_UPLOAD = 200 * 1024 * 1024
UNSAFE_NAME = re.compile(r"[^\w.\-]", re.UNICODE)
BOOK_COLS = (
    "id, name, author, cover, intro, source_type, source_url, source_id, "
    "local_path, book_group, last_read_time, create_time, has_update"
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD


def write_msg(status: int, msg: str):
    return jsonify({"message": msg}), status


def book_json(row) -> dict:
    b = dict(row)
    b["hasUpdate"] = b.get("has_update") or 0
    b["sourceType"] = b.get("source_type") or ""
    return b


def get_book_by_id(book_id: int):
    conn = require_db()
    return conn.execute(f"SELECT {BOOK_COLS} FROM book WHERE id=?", (book_id,)).fetchone()


def query_int(key: str, default: int) -> int:
    s = request.args.get(key, "")
    if not s:
        return default
    try:
        return int(s)
    except ValueError:
        return default


def save_upload() -> tuple[str, str]:
    f = request.files.get("file")
    if f is None or not f.filename:
        raise ValueError("未上传文件")
    safe = UNSAFE_NAME.sub("_", f.filename)
    name = f"{int(time.time() * 1000)}-{safe}"
    dst = upload_dir() / name
    f.save(str(dst))
    return str(dst), f.filename


def enabled_int(raw) -> int:
    if raw is None:
        return 1
    if isinstance(raw, bool):
        return 1 if raw else 0
    if isinstance(raw, (int, float)):
        return 1 if raw else 0
    s = str(raw).strip().lower()
    if s in ("", "null"):
        return 1
    if s in ("true", "1"):
        return 1
    if s in ("false", "0"):
        return 0
    try:
        return 1 if int(s) else 0
    except ValueError:
        return 1


def rule_string(raw) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, ensure_ascii=False)


# ---------- books ----------


@app.get("/api/books")
def list_books():
    keyword = (request.args.get("keyword") or "").strip()
    group = (request.args.get("group") or "").strip()
    page = query_int("page", 0)
    size = query_int("size", 20) or 20

    where = "WHERE 1=1"
    args: list = []
    if keyword:
        where += " AND (name LIKE ? OR author LIKE ?)"
        like = f"%{keyword}%"
        args.extend([like, like])
    if group:
        where += " AND book_group = ?"
        args.append(group)

    conn = require_db()
    total = conn.execute(f"SELECT COUNT(*) FROM book {where}", args).fetchone()[0]
    rows = conn.execute(
        f"SELECT {BOOK_COLS} FROM book {where} "
        "ORDER BY last_read_time DESC, create_time DESC LIMIT ? OFFSET ?",
        [*args, size, page * size],
    ).fetchall()
    return jsonify({"items": [book_json(r) for r in rows], "total": total})


@app.get("/api/books/<int:book_id>")
def get_book(book_id: int):
    b = get_book_by_id(book_id)
    if b is None:
        return write_msg(404, "书籍不存在")
    return jsonify(book_json(b))


@app.delete("/api/books/<int:book_id>")
def delete_book(book_id: int):
    b = get_book_by_id(book_id)
    if b is not None and b["local_path"]:
        try:
            os.remove(b["local_path"])
        except OSError:
            pass
    conn = require_db()
    conn.execute("DELETE FROM book WHERE id=?", (book_id,))
    conn.commit()
    return jsonify({"ok": True})


@app.get("/api/books/<int:book_id>/chapters")
def list_chapters(book_id: int):
    b = get_book_by_id(book_id)
    if b is None:
        return write_msg(404, "书籍不存在")
    if (b["source_type"] or "") == "web":
        try:
            refresh_web_chapters(dict(b))
        except Exception as e:
            return write_msg(500, str(e))
    conn = require_db()
    rows = conn.execute(
        "SELECT id, book_id, title, idx FROM chapter WHERE book_id=? ORDER BY idx",
        (book_id,),
    ).fetchall()
    out = [{"id": r["id"], "bookId": r["book_id"], "title": r["title"], "index": r["idx"]} for r in rows]
    return jsonify(out)


@app.get("/api/books/<int:book_id>/chapters/<int:cid>/content")
def get_chapter_content(book_id: int, cid: int):
    conn = require_db()
    row = conn.execute(
        "SELECT content, content_url FROM chapter WHERE id=? AND book_id=?",
        (cid, book_id),
    ).fetchone()
    if row is None:
        return write_msg(404, "章节不存在")
    content = row["content"] or ""
    content_url = row["content_url"] or ""
    if not content.strip() and content_url:
        b = get_book_by_id(book_id)
        if b is not None and (b["source_type"] or "") == "web":
            try:
                content = fetch_web_chapter(dict(b), content_url)
            except Exception as e:
                return write_msg(500, str(e))
            conn.execute("UPDATE chapter SET content=? WHERE id=?", (content, cid))
            conn.commit()
    return jsonify({"content": content})


def _serve_cover(book_id: int):
    b = get_book_by_id(book_id)
    if b is None or not b["cover"]:
        return ("", 200)
    cover = b["cover"]
    if cover.startswith("http://") or cover.startswith("https://"):
        return app.redirect(cover, code=302)
    if os.path.isfile(cover):
        return send_file(cover)
    return ("", 200)


@app.get("/api/books/<int:book_id>/cover")
def get_cover_api(book_id: int):
    return _serve_cover(book_id)


@app.get("/books/<int:book_id>/cover")
def get_cover(book_id: int):
    return _serve_cover(book_id)


@app.get("/api/books/<int:book_id>/detail")
def get_book_detail(book_id: int):
    b = get_book_by_id(book_id)
    if b is None or (b["source_type"] or "") != "web":
        return write_msg(404, "非网络书")
    try:
        detail = crawl_book_detail(dict(b))
    except Exception as e:
        return write_msg(500, str(e))
    intro = detail.intro or b["intro"]
    author = detail.author or b["author"]
    cover = detail.cover or b["cover"]
    conn = require_db()
    conn.execute(
        "UPDATE book SET intro=?, author=?, cover=? WHERE id=?",
        (intro, author, cover, book_id),
    )
    conn.commit()
    out = book_json(b)
    out["intro"] = intro
    out["author"] = author
    out["cover"] = cover
    return jsonify(out)


@app.post("/api/books/import/txt")
def import_txt():
    try:
        path, orig = save_upload()
    except Exception:
        return write_msg(400, "未上传文件")
    try:
        return jsonify(import_txt_file(path, orig))
    except Exception as e:
        return jsonify({"failed": 1, "message": str(e)}), 500


@app.post("/api/books/import/epub")
def import_epub():
    try:
        path, orig = save_upload()
    except Exception:
        return write_msg(400, "未上传文件")
    try:
        return jsonify(import_epub_file(path, orig))
    except Exception as e:
        return jsonify({"failed": 1, "message": str(e)}), 500


@app.post("/api/books/import/pdf")
def import_pdf():
    try:
        path, orig = save_upload()
    except Exception:
        return write_msg(400, "未上传文件")
    try:
        return jsonify(import_pdf_file(path, orig))
    except Exception as e:
        return jsonify({"failed": 1, "message": str(e)}), 500


# ---------- sources ----------


@app.get("/api/sources")
def list_sources():
    conn = require_db()
    rows = conn.execute(
        "SELECT id, name, url, enabled, rule, create_time FROM book_source ORDER BY id"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/sources")
def create_source():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    url = (body.get("url") or "").strip()
    if not name or not url:
        return write_msg(400, "缺少名称或URL")
    rule = rule_string(body.get("rule"))
    now = int(time.time() * 1000)
    conn = require_db()
    cur = conn.execute(
        "INSERT INTO book_source (name, url, rule, create_time) VALUES (?, ?, ?, ?)",
        (name, url, rule, now),
    )
    conn.commit()
    return jsonify(
        {
            "id": int(cur.lastrowid),
            "name": name,
            "url": url,
            "rule": rule,
            "enabled": 1,
            "create_time": now,
        }
    )


@app.put("/api/sources/<int:sid>")
def update_source(sid: int):
    body = request.get_json(silent=True) or {}
    enabled = enabled_int(body.get("enabled"))
    rule = rule_string(body.get("rule"))
    conn = require_db()
    conn.execute(
        "UPDATE book_source SET name=?, url=?, rule=?, enabled=? WHERE id=?",
        (body.get("name") or "", body.get("url") or "", rule, enabled, sid),
    )
    conn.commit()
    return jsonify({"ok": True})


@app.delete("/api/sources/<int:sid>")
def delete_source(sid: int):
    conn = require_db()
    conn.execute("DELETE FROM book_source WHERE id=?", (sid,))
    conn.commit()
    return jsonify({"ok": True})


@app.post("/api/sources/import")
def import_source_url():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    if not url:
        return write_msg(400, "缺少订阅URL")
    try:
        text = fetch_url(url)
    except Exception as e:
        return jsonify({"failed": 1, "message": str(e)}), 500
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return jsonify({"failed": 1, "message": "订阅内容不是合法 JSON"}), 500
    name = (body.get("name") or "").strip() or "订阅导入"
    inserted = 0
    first_id = 0
    for nm, rule in split_legado_rules(name, text):
        try:
            rid = legado_rule_insert(nm, rule)
        except Exception:
            continue
        if first_id == 0:
            first_id = rid
        inserted += 1
    if first_id == 0:
        return jsonify({"failed": 1, "message": "订阅中无有效书源"}), 500
    try:
        rule_obj = json.loads(text)
    except json.JSONDecodeError:
        rule_obj = text
    return jsonify(
        {"id": first_id, "count": inserted, "name": name, "url": url, "rule": rule_obj, "enabled": 1}
    )


@app.get("/api/settings")
def get_settings():
    return jsonify({"proxy": get_proxy()})


@app.post("/api/settings")
def update_settings():
    body = request.get_json(silent=True) or {}
    proxy = (body.get("proxy") or "").strip()
    set_proxy(proxy)
    return jsonify({"ok": True, "proxy": get_proxy()})


@app.get("/api/search/all")
def search_all():
    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return write_msg(400, "缺少关键字")
    conn = require_db()
    rows = conn.execute("SELECT id, name, rule FROM book_source WHERE enabled=1").fetchall()
    from urllib.parse import quote

    results = []
    for row in rows:
        sid, name, rule_str = row["id"], row["name"], row["rule"] or ""
        rule = parse_legado_rule(rule_str)
        if rule is None or rule.search is None:
            print(f"[search] source {sid} {name}: 无搜索规则")
            results.append(
                {"sourceId": sid, "sourceName": name, "books": [], "error": "无搜索规则"}
            )
            continue
        esc = quote(keyword)
        search_url = rule.search.url
        search_url = (
            search_url.replace("{{key}}", esc)
            .replace("{{search}}", esc)
            .replace("{search}", esc)
        )
        try:
            html = fetch_url(search_url)
        except Exception as e:
            print(f"[search] source {sid} fetch err: {e} url={search_url}")
            results.append(
                {"sourceId": sid, "sourceName": name, "books": [], "error": str(e)}
            )
            continue
        print(f"[search] source {sid} url={search_url!r} len={len(html)} selector={rule.search.selector!r}")
        try:
            books = crawl_search(html, rule.search, search_url)
        except Exception as e:
            print(f"[search] source {sid} parse err: {e}")
            results.append(
                {"sourceId": sid, "sourceName": name, "books": [], "error": str(e)}
            )
            continue
        print(f"[search] source {sid} got {len(books)} books")
        results.append({"sourceId": sid, "sourceName": name, "books": books})
    return jsonify(results)


def mount_frontend():
    candidates = [
        Path(__file__).resolve().parent.parent / "frontend" / "dist",
        Path("frontend") / "dist",
    ]
    dist = None
    for c in candidates:
        if (c / "index.html").is_file():
            dist = c.resolve()
            break
    if dist is None:
        return
    print(f"static: {dist}")

    @app.get("/", defaults={"path": ""})
    @app.get("/<path:path>")
    def spa(path: str):
        if path.startswith("api/"):
            return write_msg(404, "not found")
        target = dist / path
        if target.is_file():
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")


def main():
    open_db()
    mount_frontend()
    port = os.environ.get("PORT") or "8081"
    print(f"📚 Legado Web 后端已启动: http://localhost:{port}")
    app.run(host="0.0.0.0", port=int(port), threaded=True)


if __name__ == "__main__":
    main()
