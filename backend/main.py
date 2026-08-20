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
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    text = (body.get("text") or "").strip()
    name = (body.get("name") or "").strip()

    if text:
        res = _process_and_import_payload(text, name or "文本导入")
        return jsonify(res)

    if not url:
        return write_msg(400, "缺少订阅 URL 或内容")

    try:
        fetched = fetch_url(url)
    except Exception as e:
        return jsonify({"success": False, "failed": 1, "message": f"网络请求失败：{e}"}), 500

    res = _process_and_import_payload(fetched, name or url)
    res["url"] = url
    return jsonify(res)


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
    return jsonify({"proxy": get_proxy()})


@app.post("/api/settings")
def update_settings():
    body = request.get_json(silent=True) or {}
    proxy = (body.get("proxy") or "").strip()
    set_proxy(proxy)
    return jsonify({"ok": True, "proxy": get_proxy()})


def _execute_single_source_search(sid: int, name: str, rule_str: str, keyword: str) -> dict:
    from source import fetch_search_response
    rule = parse_legado_rule(rule_str)
    if rule is None or rule.search is None or not rule.search.url:
        return {"sourceId": sid, "sourceName": name, "books": [], "error": "无搜索规则"}

    search_spec = rule.search.url
    try:
        html, final_url = fetch_search_response(search_spec, keyword)
    except Exception as e:
        return {"sourceId": sid, "sourceName": name, "books": [], "error": str(e)}

    try:
        books = crawl_search(html, rule.search, final_url)
    except Exception as e:
        print(f"[_execute_single_source_search] crawl_search error for {name}: {e}")
        return {"sourceId": sid, "sourceName": name, "books": [], "error": str(e)}

    print(f"[_execute_single_source_search] sid={sid} name={name} html_len={len(html)} books_found={len(books)}")
    for b in books:
        b["sourceId"] = sid
        b["sourceType"] = "web"
    return {"sourceId": sid, "sourceName": name, "books": books, "error": None}


@app.get("/api/search/stream")
def search_stream():
    """SSE 流式搜索：每搜完一个书源立即向前端推送一条事件数据。"""
    import queue
    from concurrent.futures import ThreadPoolExecutor

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

        executor = ThreadPoolExecutor(max_workers=min(12, total_sources))
        for r in rows:
            executor.submit(worker, r)
        executor.shutdown(wait=False)

        completed = 0
        total_books = 0
        while completed < total_sources:
            try:
                res = q.get(timeout=15.0)
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
    print(f"[Legado Web] 后端已启动: http://localhost:{port}")
    app.run(host="0.0.0.0", port=int(port), threaded=True)


if __name__ == "__main__":
    main()
