"""PDF 导入。"""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from book import insert_book_and_chapters, parse_chapters


def import_pdf_file(file_path: str, original_name: str) -> dict:
    try:
        reader = PdfReader(file_path)
    except Exception as e:
        raise ValueError(f"PDF 解析失败: {e}") from e

    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            continue
        parts.append(t if t.endswith("\n") else t + "\n")
    text = "".join(parts).strip()
    if not text:
        raise ValueError("PDF 未解析出可读文本（可能是扫描件，无文字层）")

    name = Path(original_name).stem
    chapters = parse_chapters(text)
    if not chapters:
        raise ValueError("PDF 中没有可读取的章节")
    book_id = insert_book_and_chapters(name, "", "", "pdf", file_path, chapters)
    return {"success": 1, "bookId": book_id, "chapterCount": len(chapters)}
