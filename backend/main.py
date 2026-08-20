"""Legado Web 后端（Flask + SQLite + curl_cffi）。

保持 /api 路径与 JSON 字段与原 Go 实现兼容。
网络抓取统一使用 curl_cffi impersonate=chrome120。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

# 确保 Windows 命令行支持 UTF-8 输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from flask import Flask, Response, jsonify, request, send_file, send_from_directory

from book import import_txt_file
from db import data_dir, open_db, require_db, upload_dir
from epub import import_epub_file
from pdf import import_pdf_file
from settings import get_proxy, set_proxy
from logger import (
    get_logger,
    get_memory_logs,
    clear_memory_logs,
    register_log_subscriber,
    unregister_log_subscriber,
)
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

logger = get_logger("app")

MAX_UPLOAD = 200 * 1024 * 1024
UNSAFE_NAME = re.compile(r"[^\w.\-]", re.UNICODE)
BOOK_COLS = (
    "id, uuid, name, author, cover, intro, source_type, source_url, source_id, "
    "local_path, book_group, in_bookcase, last_read_time, create_time, has_update"
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD


def write_msg(status: int, msg: str):
    return jsonify({"message": msg}), status


def book_json(row) -> dict:
    b = dict(row)
    b["hasUpdate"] = b.get("has_update") or 0
    b["sourceType"] = b.get("source_type") or ""
    b["inBookcase"] = 1 if (b.get("in_bookcase") is None or b.get("in_bookcase") == 1) else 0
    b["uuid"] = b.get("uuid") or ""
    return b


def get_book_by_id_or_uuid(identifier: str | int):
    conn = require_db()
    s = str(identifier).strip()
    if s.isdigit():
        row = conn.execute(f"SELECT {BOOK_COLS} FROM book WHERE id=? OR uuid=?", (int(s), s)).fetchone()
    else:
        row = conn.execute(f"SELECT {BOOK_COLS} FROM book WHERE uuid=?", (s,)).fetchone()
    return row


get_book_by_id = get_book_by_id_or_uuid


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

    where = "WHERE (in_bookcase IS NULL OR in_bookcase = 1)"
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


@app.post("/api/books/batch-delete")
def batch_delete_books():
    body = request.get_json(silent=True) or {}
    identifiers = body.get("identifiers") or body.get("ids") or []
    if not identifiers:
        return jsonify({"ok": True, "count": 0})

    conn = require_db()
    deleted = 0
    for ident in identifiers:
        b = get_book_by_id(ident)
        if b is not None:
            if b["local_path"]:
                try:
                    os.remove(b["local_path"])
                except OSError:
                    pass
            conn.execute("DELETE FROM book WHERE id=?", (b["id"],))
            deleted += 1
    conn.commit()
    return jsonify({"ok": True, "count": deleted})


@app.get("/api/books/<identifier>")
def get_book(identifier: str):
    b = get_book_by_id(identifier)
    if b is None:
        return write_msg(404, "书籍不存在")
    return jsonify(book_json(b))


@app.delete("/api/books/<identifier>")
def delete_book(identifier: str):
    b = get_book_by_id(identifier)
    if b is not None and b["local_path"]:
        try:
            os.remove(b["local_path"])
        except OSError:
            pass
    if b is not None:
        conn = require_db()
        conn.execute("DELETE FROM book WHERE id=?", (b["id"],))
        conn.commit()
    return jsonify({"ok": True})


@app.post("/api/books/<identifier>/add-to-shelf")
def add_book_to_shelf(identifier: str):
    b = get_book_by_id(identifier)
    if b is None:
        return write_msg(404, "书籍不存在")
    now = int(time.time() * 1000)
    conn = require_db()
    conn.execute("UPDATE book SET in_bookcase=1, create_time=? WHERE id=?", (now, b["id"]))
    conn.commit()
    saved = get_book_by_id(b["id"])
    return jsonify(book_json(saved))


@app.get("/api/books/<identifier>/chapters")
def list_chapters(identifier: str):
    b = get_book_by_id(identifier)
    if b is None:
        return write_msg(404, "书籍不存在")
    book_id = b["id"]
    conn = require_db()
    # 检查是否已有章节
    existing_count = conn.execute("SELECT COUNT(*) FROM chapter WHERE book_id=?", (book_id,)).fetchone()[0]
    if existing_count == 0 and (b["source_type"] or "") == "web":
        try:
            refresh_web_chapters(dict(b))
        except Exception as e:
            print(f"[chapters] refresh book {book_id} failed: {e}")
            return write_msg(502, f"解析章节列表失败：{e}")

    rows = conn.execute(
        "SELECT id, book_id, title, idx FROM chapter WHERE book_id=? ORDER BY idx",
        (book_id,),
    ).fetchall()
    out = [{"id": r["id"], "bookId": r["book_id"], "title": r["title"], "index": r["idx"]} for r in rows]
    return jsonify(out)


@app.get("/api/books/<identifier>/chapters/<int:cid>/content")
def get_chapter_content(identifier: str, cid: int):
    b = get_book_by_id(identifier)
    if b is None:
        return write_msg(404, "书籍不存在")
    book_id = b["id"]
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
        if (b["source_type"] or "") == "web":
            try:
                content = fetch_web_chapter(dict(b), content_url)
            except Exception as e:
                return write_msg(500, f"解析章节数据失败：{e}")
            conn.execute("UPDATE chapter SET content=? WHERE id=?", (content, cid))
            conn.commit()
    return jsonify({"content": content})


@app.get("/api/books/<identifier>/progress")
def get_read_progress(identifier: str):
    b = get_book_by_id(identifier)
    if b is None:
        return write_msg(404, "书籍不存在")
    book_id = b["id"]
    conn = require_db()
    row = conn.execute(
        "SELECT chapter_id, chapter_idx, pos, update_time FROM read_progress WHERE book_id=?",
        (book_id,),
    ).fetchone()
    if row is None:
        return jsonify({"bookId": book_id, "chapterId": 0, "chapterIndex": 0, "pos": 0, "updateTime": 0})
    return jsonify({
        "bookId": book_id,
        "chapterId": row["chapter_id"],
        "chapterIndex": row["chapter_idx"],
        "pos": row["pos"],
        "updateTime": row["update_time"],
    })


@app.post("/api/books/<identifier>/progress")
def save_read_progress(identifier: str):
    b = get_book_by_id(identifier)
    if b is None:
        return write_msg(404, "书籍不存在")
    book_id = b["id"]
    body = request.get_json(silent=True) or {}
    chapter_id = int(body.get("chapterId") or body.get("chapter_id") or 0)
    chapter_idx = int(body.get("chapterIndex") or body.get("chapter_idx") or 0)
    pos = float(body.get("pos") or 0.0)
    now = int(time.time() * 1000)

    conn = require_db()
    conn.execute(
        """
        INSERT INTO read_progress (book_id, chapter_id, chapter_idx, pos, update_time)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(book_id) DO UPDATE SET
            chapter_id = excluded.chapter_id,
            chapter_idx = excluded.chapter_idx,
            pos = excluded.pos,
            update_time = excluded.update_time
        """,
        (book_id, chapter_id, chapter_idx, pos, now),
    )
    # 更新书籍最近阅读时间和历史记录
    conn.execute("UPDATE book SET last_read_time=? WHERE id=?", (now, book_id))
    conn.execute(
        """
        INSERT INTO history (book_id, read_time)
        VALUES (?, ?)
        ON CONFLICT(book_id) DO UPDATE SET read_time = excluded.read_time
        """,
        (book_id, now),
    )
    conn.commit()
    return jsonify({"ok": True})


def _generate_default_cover_svg(title: str = "书") -> Response:
    short_title = (title or "书")[:4]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 220" width="160" height="220">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#4a3728"/>
      <stop offset="100%" stop-color="#2a1f18"/>
    </linearGradient>
  </defs>
  <rect width="160" height="220" rx="6" fill="url(#bg)"/>
  <line x1="12" y1="0" x2="12" y2="220" stroke="rgba(255,255,255,0.1)" stroke-width="2"/>
  <rect x="22" y="26" width="116" height="168" rx="3" fill="none" stroke="rgba(184,134,58,0.35)" stroke-width="1.5"/>
  <text x="80" y="118" fill="#e6d5b8" font-size="18" font-family="'Noto Serif SC', 'Songti SC', serif" font-weight="600" text-anchor="middle">{short_title}</text>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")


def _serve_cover_by_book(b):
    if b is None or not b["cover"]:
        return _generate_default_cover_svg(b["name"] if b else "书")
    cover = b["cover"]
    if cover.startswith("http://") or cover.startswith("https://"):
        return app.redirect(cover, code=302)
    if os.path.isfile(cover):
        return send_file(cover)
    return _generate_default_cover_svg(b["name"] if b else "书")


@app.get("/api/books/<identifier>/cover")
def get_cover_api(identifier: str):
    b = get_book_by_id(identifier)
    return _serve_cover_by_book(b)


@app.get("/books/<identifier>/cover")
def get_cover(identifier: str):
    b = get_book_by_id(identifier)
    return _serve_cover_by_book(b)


@app.get("/api/books/<identifier>/detail")
def get_book_detail(identifier: str):
    b = get_book_by_id(identifier)
    if b is None or (b["source_type"] or "") != "web":
        return write_msg(404, "非网络书")
    book_id = b["id"]
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


@app.post("/api/books/init-preview")
@app.post("/api/books/from-search")
def add_from_search():
    """将搜索结果注册到数据库。支持预生成的 UUID 和 in_bookcase（默认0不入书架，或1入书架）。"""
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    book_url = (body.get("bookUrl") or body.get("source_url") or body.get("sourceUrl") or "").strip()
    uuid_val = (body.get("uuid") or "").strip()
    in_bookcase = 1 if body.get("inBookcase") is True or body.get("in_bookcase") == 1 else 0

    try:
        source_id = int(body.get("sourceId") or body.get("source_id") or 0)
    except (TypeError, ValueError):
        source_id = 0
    if not name or not book_url:
        return write_msg(400, "缺少书名或书籍地址")
    if not source_id:
        return write_msg(400, "缺少书源")

    conn = require_db()
    # 优先根据 uuid 查找
    existing = None
    if uuid_val:
        existing = conn.execute("SELECT id FROM book WHERE uuid=?", (uuid_val,)).fetchone()
    if not existing:
        existing = conn.execute(
            "SELECT id, uuid FROM book WHERE source_url=? AND source_id=?",
            (book_url, source_id),
        ).fetchone()

    if existing:
        book_id = int(existing["id"])
        # 如果已有记录但未设置 uuid，补充 uuid
        if uuid_val and not (existing["uuid"] if "uuid" in existing.keys() else ""):
            conn.execute("UPDATE book SET uuid=? WHERE id=?", (uuid_val, book_id))
            conn.commit()
        if in_bookcase == 1:
            conn.execute("UPDATE book SET in_bookcase=1 WHERE id=?", (book_id,))
            conn.commit()
        return jsonify(book_json(get_book_by_id(book_id)))

    now = int(time.time() * 1000)
    cur = conn.execute(
        "INSERT INTO book (uuid, name, author, cover, intro, source_type, source_url, source_id, in_bookcase, create_time) "
        "VALUES (?, ?, ?, ?, ?, 'web', ?, ?, ?, ?)",
        (
            uuid_val,
            name,
            body.get("author") or "",
            body.get("cover") or "",
            body.get("intro") or "",
            book_url,
            source_id,
            in_bookcase,
            now,
        ),
    )
    conn.commit()
    saved = get_book_by_id(int(cur.lastrowid))
    if saved is None:
        return write_msg(500, "初始化书籍失败")
    return jsonify(book_json(saved))


# ---------- preview（免入库实时预览）----------


@app.post("/api/preview/toc")
def preview_toc():
    """根据 bookUrl + sourceId 实时抓取目录，不写入数据库。"""
    body = request.get_json(silent=True) or {}
    try:
        source_id = int(body.get("sourceId") or body.get("source_id") or 0)
    except (TypeError, ValueError):
        source_id = 0
    book_url = (body.get("bookUrl") or body.get("source_url") or "").strip()
    if not source_id or not book_url:
        return write_msg(400, "缺少 sourceId 或 bookUrl")

    from source import source_by_id, _rule_for_source, _toc_url, crawl_toc, fetch_url

    src = source_by_id(source_id)
    if not src:
        return write_msg(404, "书源不存在")
    try:
        rule = _rule_for_source(src)
    except ValueError as e:
        return write_msg(400, str(e))
    if rule.toc is None or not rule.toc.selector:
        return write_msg(400, "该书源无目录规则")

    fake_book = {"source_id": source_id, "source_url": book_url, "id": 0}
    toc_url = _toc_url(fake_book, rule)
    if not toc_url:
        return write_msg(400, "无法确定目录地址")
    try:
        html = fetch_url(toc_url)
    except Exception as e:
        return write_msg(502, f"目录抓取失败：{e}")
    chapters = crawl_toc(html, rule.toc, toc_url)
    return jsonify(
        [{"index": i, "title": c["title"], "chapterUrl": c["chapterUrl"]} for i, c in enumerate(chapters)]
    )


@app.post("/api/preview/content")
def preview_content():
    """根据 chapterUrl + sourceId 实时抓取章节正文，不写入数据库。"""
    body = request.get_json(silent=True) or {}
    try:
        source_id = int(body.get("sourceId") or body.get("source_id") or 0)
    except (TypeError, ValueError):
        source_id = 0
    chapter_url = (body.get("chapterUrl") or "").strip()
    if not source_id or not chapter_url:
        return write_msg(400, "缺少 sourceId 或 chapterUrl")

    from source import source_by_id, _rule_for_source, fetch_web_chapter

    fake_book = {"source_id": source_id, "source_url": "", "id": 0}
    try:
        content = fetch_web_chapter(fake_book, chapter_url)
    except Exception as e:
        return write_msg(502, f"章节抓取失败：{e}")
    return jsonify({"content": content})


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
    page_str = request.args.get("page")
    size_str = request.args.get("size")
    keyword = (request.args.get("keyword") or "").strip()
    enabled_str = request.args.get("enabled")

    conn = require_db()

    # 如果传了 page/size 则返回分页结构，否则返回全量数组保证兼容性
    if page_str is not None and size_str is not None:
        try:
            page = max(0, int(page_str))
            size = max(1, min(500, int(size_str)))
        except ValueError:
            page, size = 0, 20

        where = []
        args = []
        if keyword:
            where.append("(name LIKE ? OR url LIKE ?)")
            args.extend([f"%{keyword}%", f"%{keyword}%"])
        if enabled_str in ("1", "0", "true", "false"):
            en_val = 1 if enabled_str in ("1", "true") else 0
            where.append("enabled = ?")
            args.append(en_val)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        total = conn.execute(f"SELECT COUNT(*) as c FROM book_source {where_sql}", args).fetchone()["c"]
        rows = conn.execute(
            f"SELECT id, name, url, enabled, rule, create_time FROM book_source {where_sql} ORDER BY id DESC LIMIT ? OFFSET ?",
            [*args, size, page * size],
        ).fetchall()
        return jsonify({"items": [dict(r) for r in rows], "total": total})

    # 全量查询
    rows = conn.execute(
        "SELECT id, name, rule, url, enabled, create_time FROM book_source ORDER BY id DESC"
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


@app.post("/api/sources/batch-delete")
def batch_delete_sources():
    body = request.get_json(silent=True) or {}
    raw_ids = body.get("ids") or []
    if not isinstance(raw_ids, list) or not raw_ids:
        return write_msg(400, "缺少要删除的书源 ID 列表")

    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        return write_msg(400, "书源 ID 列表格式错误")

    conn = require_db()
    placeholders = ",".join("?" for _ in ids)
    conn.execute(f"DELETE FROM book_source WHERE id IN ({placeholders})", ids)
    conn.commit()
    return jsonify({"ok": True, "deletedCount": len(ids)})


@app.post("/api/sources/batch-toggle")
def batch_toggle_sources():
    body = request.get_json(silent=True) or {}
    raw_ids = body.get("ids") or []
    enabled = 1 if body.get("enabled") in (True, 1, "1") else 0
    if not isinstance(raw_ids, list) or not raw_ids:
        return write_msg(400, "缺少书源 ID 列表")

    ids = [int(x) for x in raw_ids if str(x).isdigit()]
    if not ids:
        return write_msg(400, "书源 ID 列表格式错误")

    conn = require_db()
    placeholders = ",".join("?" for _ in ids)
    conn.execute(f"UPDATE book_source SET enabled=? WHERE id IN ({placeholders})", [enabled, *ids])
    conn.commit()
    return jsonify({"ok": True, "updatedCount": len(ids), "enabled": enabled})


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


def _process_and_import_payload(text: str, default_name: str = "") -> dict:
    from source import parse_sources_from_payload, legado_rule_upsert
    sources = parse_sources_from_payload(text, default_name)
    if not sources:
        return {"success": False, "count": 0, "inserted": 0, "updated": 0, "message": "未解析到有效书源规则"}

    inserted_count = 0
    updated_count = 0
    first_id = 0
    sample_names = []

    for name, source_url, rule_str in sources:
        try:
            sid, is_new = legado_rule_upsert(name, source_url, rule_str)
            if first_id == 0:
                first_id = sid
            if is_new:
                inserted_count += 1
            else:
                updated_count += 1
            if len(sample_names) < 5:
                sample_names.append(name)
        except Exception as e:
            print(f"[import] upsert error for {name}: {e}")
            continue

    total = inserted_count + updated_count
    if total == 0:
        return {"success": False, "count": 0, "message": "书源入库失败，请检查规则格式"}

    return {
        "success": True,
        "count": total,
        "inserted": inserted_count,
        "updated": updated_count,
        "firstId": first_id,
        "sample": sample_names,
        "message": f"成功导入 {total} 个书源（新增 {inserted_count} 个，更新 {updated_count} 个）",
    }


@app.post("/api/sources/import")
@app.post("/api/sources/import/url")
def import_source_url():
    """多种形式导入：支持网络 URL 订阅、合集页面解析、或者直接传 text。"""
    from source import fetch_subscription_url
    from settings import get_timeout

    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    text = (body.get("text") or "").strip()
    name = (body.get("name") or "").strip()
    try:
        custom_timeout = int(body.get("timeout", 0))
    except (ValueError, TypeError):
        custom_timeout = 0
    timeout = max(5, min(180, custom_timeout or max(30, get_timeout())))

    if text:
        res = _process_and_import_payload(text, name or "文本导入")
        return jsonify(res)

    if not url:
        return write_msg(400, "缺少订阅 URL 或内容")

    logger.info("开始网络导入书源: %s (超时设定: %ds)...", url, timeout)
    try:
        fetched, elapsed_ms = fetch_subscription_url(url, timeout=timeout)
        logger.info("书源订阅下载成功: %s, 耗时 %dms, 大小 %d 字节", url, elapsed_ms, len(fetched))
    except Exception as e:
        logger.warning("书源订阅下载失败 [%s]: %s", url, e)
        return jsonify({
            "success": False,
            "failed": 1,
            "message": f"网络请求超时或失败（已等待 {timeout} 秒）：{e}，建议检查代理配置或复制规则文本直接导入",
        }), 500

    res = _process_and_import_payload(fetched, name or url)
    res["url"] = url
    res["elapsedMs"] = elapsed_ms
    res["message"] = f"下载耗时 {elapsed_ms / 1000:.1f}s，" + res.get("message", "")
    return jsonify(res)


@app.post("/api/sources/<int:sid>/test-delay")
def test_single_source_delay(sid: int):
    """测试单个书源的响应延迟。"""
    from source import test_source_latency
    conn = require_db()
    row = conn.execute("SELECT id, name, url, rule FROM book_source WHERE id=?", (sid,)).fetchone()
    if not row:
        return write_msg(404, "书源不存在")

    res = test_source_latency(row["id"], row["name"], row["url"] or "", row["rule"] or "")
    return jsonify(res)


@app.post("/api/sources/batch-test-delay")
def batch_test_sources_delay():
    """并发批量测速已选或所有书源。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from source import test_source_latency

    body = request.get_json(silent=True) or {}
    source_ids = body.get("sourceIds") or []
    conn = require_db()

    if source_ids and isinstance(source_ids, list):
        placeholders = ",".join("?" for _ in source_ids)
        rows = conn.execute(
            f"SELECT id, name, url, rule FROM book_source WHERE id IN ({placeholders})",
            source_ids,
        ).fetchall()
    else:
        rows = conn.execute("SELECT id, name, url, rule FROM book_source").fetchall()

    if not rows:
        return jsonify([])

    from settings import get_proxy
    active_proxy = get_proxy()
    results = []
    with ThreadPoolExecutor(max_workers=min(16, len(rows))) as executor:
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
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"sourceId": futures[f], "success": False, "delay": -1, "error": str(e)})

    return jsonify(results)


@app.post("/api/sources/import/file")
def import_source_file():
    """本地书源文件导入（支持 .json 或 .txt 批量书源文件）。"""
    try:
        path, orig_name = save_upload()
    except Exception:
        return write_msg(400, "未上传文件")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return jsonify({"success": False, "message": f"文件读取失败：{e}"}), 500

    res = _process_and_import_payload(content, orig_name)
    return jsonify(res)


@app.get("/api/sources/presets")
def get_source_presets():
    """内置推荐优质书源订阅源合集。"""
    presets = [
        {
            "name": "一程书源合集 (yckceo 精品源)",
            "url": "https://www.yckceo.com/yuedu/rss/index.html",
            "desc": "汇聚全网数百个优质小说源，实时维护更新",
        },
        {
            "name": "源仓库优质订阅源",
            "url": "https://raw.githubusercontent.com/gedoor/legado/master/README.md",
            "desc": "包含热门精选、全网出版物与网络文学书源",
        },
        {
            "name": "半山人小说精选源",
            "url": "https://www.banshanren.com",
            "desc": "热门玄幻、都市小说极速书源",
        },
    ]
    return jsonify(presets)


@app.get("/api/settings")
def get_settings():
    from settings import (
        get_proxy,
        get_timeout,
        get_max_workers,
        get_health_check_enabled,
        get_health_check_interval,
        get_auto_disable_dead,
    )
    return jsonify({
        "proxy": get_proxy(),
        "timeout": get_timeout(),
        "max_workers": get_max_workers(),
        "health_check_enabled": get_health_check_enabled(),
        "health_check_interval": get_health_check_interval(),
        "auto_disable_dead": get_auto_disable_dead(),
    })


@app.post("/api/settings")
def update_settings():
    from settings import (
        get_proxy,
        set_proxy,
        get_timeout,
        set_timeout,
        get_max_workers,
        set_max_workers,
        get_health_check_enabled,
        set_health_check_enabled,
        get_health_check_interval,
        set_health_check_interval,
        get_auto_disable_dead,
        set_auto_disable_dead,
    )
    body = request.get_json(silent=True) or {}
    if "proxy" in body:
        set_proxy(str(body.get("proxy") or "").strip())
    if "timeout" in body:
        set_timeout(body.get("timeout"))
    if "max_workers" in body or "maxWorkers" in body:
        set_max_workers(body.get("max_workers") or body.get("maxWorkers"))
    if "health_check_enabled" in body or "healthCheckEnabled" in body:
        set_health_check_enabled(body.get("health_check_enabled") if "health_check_enabled" in body else body.get("healthCheckEnabled"))
    if "health_check_interval" in body or "healthCheckInterval" in body:
        set_health_check_interval(body.get("health_check_interval") or body.get("healthCheckInterval"))
    if "auto_disable_dead" in body or "autoDisableDead" in body:
        set_auto_disable_dead(body.get("auto_disable_dead") if "auto_disable_dead" in body else body.get("autoDisableDead"))

    logger.info("系统设置已更新: proxy=%s, timeout=%s, max_workers=%s, health_check=%s(%sh), auto_disable_dead=%s",
        get_proxy(), get_timeout(), get_max_workers(), get_health_check_enabled(), get_health_check_interval(), get_auto_disable_dead())
    return jsonify({
        "ok": True,
        "proxy": get_proxy(),
        "timeout": get_timeout(),
        "max_workers": get_max_workers(),
        "health_check_enabled": get_health_check_enabled(),
        "health_check_interval": get_health_check_interval(),
        "auto_disable_dead": get_auto_disable_dead(),
    })


@app.post("/api/settings/test-proxy")
def test_proxy_route():
    """测试指定的网络代理连通性、出口 IP 与延迟。"""
    from settings import test_proxy_connection
    body = request.get_json(silent=True) or {}
    proxy = (body.get("proxy") or "").strip()
    res = test_proxy_connection(proxy)
    if res.get("ok"):
        logger.info("代理连通性测试成功: 代理=%s, 出口IP=%s, 延迟=%dms", res.get("proxy"), res.get("ip"), res.get("delay"))
    else:
        logger.warning("代理连通性测试失败: 代理=%s, 错误=%s", res.get("proxy"), res.get("error"))
    return jsonify(res)


@app.get("/api/sources/health/status")
def get_sources_health_status():
    """获取书源健康巡检状态与最近一次扫描结果。"""
    from health import health_manager
    return jsonify(health_manager.get_status())


@app.post("/api/sources/health/run")
def trigger_sources_health_check():
    """手动立即触发全量书源健康体检。"""
    import threading
    from health import health_manager
    status = health_manager.get_status()
    if status.get("scanning"):
        return jsonify({"ok": False, "message": "已有正在进行的体检任务，请稍候"}), 400

    threading.Thread(target=health_manager.run_scan, kwargs={"manual": True}, daemon=True).start()
    return jsonify({"ok": True, "message": "已在后台启动全量书源健康体检"})


@app.post("/api/sources/health/disable-dead")
def disable_dead_sources_route():
    """一键禁用当前体检识别到的所有失效书源。"""
    from health import health_manager
    count = health_manager.disable_dead_sources()
    return jsonify({"ok": True, "disabledCount": count, "message": f"已成功禁用 {count} 个失效书源"})


@app.post("/api/sources/health/delete-dead")
def delete_dead_sources_route():
    """一键删除当前体检识别到的所有失效书源。"""
    from health import health_manager
    count = health_manager.delete_dead_sources()
    return jsonify({"ok": True, "deletedCount": count, "message": f"已成功删除 {count} 个失效书源"})


@app.get("/api/logs")
def list_logs():
    """获取服务端内存缓冲中的结构化日志。"""
    level = request.args.get("level", "ALL")
    keyword = request.args.get("keyword", "")
    try:
        limit = min(1000, max(10, int(request.args.get("limit", 200))))
    except ValueError:
        limit = 200
    try:
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        offset = 0

    return jsonify(get_memory_logs(level=level, keyword=keyword, limit=limit, offset=offset))


@app.post("/api/logs/clear")
def clear_logs():
    """清空服务端内存中的日志缓冲区。"""
    clear_memory_logs()
    logger.info("已清空内存日志缓冲区")
    return jsonify({"ok": True, "message": "日志已清空"})


@app.get("/api/logs/stream")
def stream_logs():
    """SSE 实时推送新产生的系统日志。"""
    import queue
    q = register_log_subscriber()

    def generate():
        try:
            yield f"data: {json.dumps({'type': 'connected'}, ensure_ascii=False)}\n\n"
            while True:
                try:
                    item = q.get(timeout=15.0)
                    yield f"data: {json.dumps({'type': 'log', 'data': item}, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"
        finally:
            unregister_log_subscriber(q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _execute_single_source_search(sid: int, name: str, rule_str: str, keyword: str) -> dict:
    from source import fetch_search_response
    from settings import get_timeout
    rule = parse_legado_rule(rule_str)
    if rule is None or rule.search is None or not rule.search.url:
        logger.warning("[%s (ID:%s)] 缺少有效搜索规则", name, sid)
        return {"sourceId": sid, "sourceName": name, "books": [], "error": "无搜索规则"}

    search_spec = rule.search.url
    timeout = get_timeout()
    try:
        html, final_url = fetch_search_response(search_spec, keyword, timeout=timeout, base_url=rule.base_url)
    except Exception as e:
        logger.warning("[%s (ID:%s)] 搜索请求失败: %s", name, sid, e)
        return {"sourceId": sid, "sourceName": name, "books": [], "error": str(e)}

    try:
        books = crawl_search(html, rule.search, final_url)
    except Exception as e:
        logger.warning("[%s (ID:%s)] 规则解析失败: %s", name, sid, e)
        return {"sourceId": sid, "sourceName": name, "books": [], "error": str(e)}

    logger.info("[%s (ID:%s)] 检索「%s」完成: 返回 %d 本书", name, sid, keyword, len(books))
    for b in books:
        b["sourceId"] = sid
        b["sourceType"] = "web"
    return {"sourceId": sid, "sourceName": name, "books": books, "error": None}


@app.get("/api/search/stream")
def search_stream():
    """SSE 流式搜索：每搜完一个书源立即向前端推送一条事件数据。"""
    import queue
    from concurrent.futures import ThreadPoolExecutor
    from settings import get_max_workers

    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return write_msg(400, "缺少关键字")
    source_ids_str = (request.args.get("sourceIds") or "").strip()

    conn = require_db()
    if source_ids_str:
        sids = [int(x) for x in source_ids_str.split(",") if x.strip().isdigit()]
        if sids:
            placeholders = ",".join("?" for _ in sids)
            rows = conn.execute(
                f"SELECT id, name, rule FROM book_source WHERE enabled=1 AND id IN ({placeholders})",
                sids,
            ).fetchall()
        else:
            rows = conn.execute("SELECT id, name, rule FROM book_source WHERE enabled=1").fetchall()
    else:
        rows = conn.execute("SELECT id, name, rule FROM book_source WHERE enabled=1").fetchall()

    logger.info("发起流式多源搜索: 关键词「%s」, 启用书源数: %d", keyword, len(rows))

    def generate():
        total_sources = len(rows)
        yield f"data: {json.dumps({'type': 'start', 'totalSources': total_sources}, ensure_ascii=False)}\n\n"

        if total_sources == 0:
            yield f"data: {json.dumps({'type': 'done', 'totalBooks': 0}, ensure_ascii=False)}\n\n"
            return

        q = queue.Queue()

        def worker(row):
            res = _execute_single_source_search(row["id"], row["name"], row["rule"] or "", keyword)
            q.put(res)

        workers = min(get_max_workers(), max(1, total_sources))
        executor = ThreadPoolExecutor(max_workers=workers)
        for r in rows:
            executor.submit(worker, r)
        executor.shutdown(wait=False)

        completed = 0
        total_books = 0
        while completed < total_sources:
            try:
                res = q.get(timeout=30.0)
                completed += 1
                total_books += len(res.get("books", []))
                payload = {
                    "type": "source_result",
                    "completed": completed,
                    "totalSources": total_sources,
                    **res,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            except queue.Empty:
                break

        logger.info("流式搜索完成: 关键词「%s」, 共检索到 %d 本书籍", keyword, total_books)
        yield f"data: {json.dumps({'type': 'done', 'totalBooks': total_books}, ensure_ascii=False)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/search/all")
def search_all():
    """标准并发搜索：多线程并发检索后统一返回。"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from settings import get_max_workers

    keyword = (request.args.get("keyword") or "").strip()
    if not keyword:
        return write_msg(400, "缺少关键字")
    source_ids_str = (request.args.get("sourceIds") or "").strip()

    conn = require_db()
    if source_ids_str:
        sids = [int(x) for x in source_ids_str.split(",") if x.strip().isdigit()]
        if sids:
            placeholders = ",".join("?" for _ in sids)
            rows = conn.execute(
                f"SELECT id, name, rule FROM book_source WHERE enabled=1 AND id IN ({placeholders})",
                sids,
            ).fetchall()
        else:
            rows = conn.execute("SELECT id, name, rule FROM book_source WHERE enabled=1").fetchall()
    else:
        rows = conn.execute("SELECT id, name, rule FROM book_source WHERE enabled=1").fetchall()

    results = []
    if rows:
        with ThreadPoolExecutor(max_workers=min(12, len(rows))) as executor:
            futures = [
                executor.submit(
                    _execute_single_source_search,
                    r["id"],
                    r["name"],
                    r["rule"] or "",
                    keyword,
                )
                for r in rows
            ]
            for f in as_completed(futures):
                try:
                    results.append(f.result())
                except Exception:
                    pass

    return jsonify(results)


def mount_frontend():
    candidates = [
        Path(__file__).resolve().parent.parent / "frontend" / "dist",
        Path(__file__).resolve().parent / "dist",
        Path("frontend") / "dist",
        Path("dist"),
        Path("/app/dist"),
        Path("/app/frontend/dist"),
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
    from health import health_manager
    open_db()
    health_manager.start()
    mount_frontend()
    port = os.environ.get("PORT") or "4388"
    print(f"[Legado Web] 后端已启动: http://localhost:{port}")
    app.run(host="0.0.0.0", port=int(port), threaded=True)


if __name__ == "__main__":
    main()
