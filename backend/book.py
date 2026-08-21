"""TXT 导入与章节切分。"""
from __future__ import annotations

import os
import re
from pathlib import Path

from db import require_db

TITLE_RE = re.compile(
    r"^[ \t]*(第\s*[0-9零一二三四五六七八九十百千万两a-zA-Z]+\s*[章节回卷集部篇]|第\s*[0-9零一二三四五六七八九十百千万两a-zA-Z]+\s*话|卷\s*[0-9零一二三四五六七八九十百千万两]+|Chapter\s*\d+|序章|楔子|番外(?:篇)?|完结感言|正文卷|\b正文(?:\s+[^\n]+)?$)[^\n]{0,50}",
    re.MULTILINE | re.IGNORECASE,
)


def decode_text(raw: bytes) -> str:
    utf8 = raw.decode("utf-8", errors="replace")
    if "�" not in utf8:
        return utf8
    try:
        return raw.decode("gb18030")
    except Exception:
        return utf8


def parse_chapters(text: str) -> list[dict]:
    matches = list(TITLE_RE.finditer(text))
    if not matches:
        return [{"title": "正文", "content": text.strip()}]

    chapters: list[dict] = []
    for i, m in enumerate(matches):
        title = m.group(0).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            chapters.append({"title": title, "content": content})

    intro = text[: matches[0].start()].strip()
    if intro:
        chapters = [{"title": "序言", "content": intro}, *chapters]
    return chapters


def insert_book_and_chapters(
    name: str,
    author: str,
    cover: str,
    source_type: str,
    local_path: str,
    chapters: list[dict],
) -> int:
    conn = require_db()
    now = int(__import__("time").time() * 1000)
    cur = conn.execute(
        "INSERT INTO book (name, author, cover, source_type, local_path, create_time) VALUES (?, ?, ?, ?, ?, ?)",
        (name, author, cover, source_type, local_path, now),
    )
    book_id = int(cur.lastrowid)
    conn.executemany(
        "INSERT INTO chapter (book_id, title, idx, content) VALUES (?, ?, ?, ?)",
        [(book_id, c["title"], i, c["content"]) for i, c in enumerate(chapters)],
    )
    conn.commit()
    return book_id


def import_txt_file(file_path: str, original_name: str) -> dict:
    raw = Path(file_path).read_bytes()
    text = decode_text(raw)
    name = Path(original_name).stem or Path(file_path).stem
    chapters = parse_chapters(text)
    book_id = insert_book_and_chapters(name, "", "", "txt", file_path, chapters)
    return {"success": 1, "bookId": book_id, "chapterCount": len(chapters)}
