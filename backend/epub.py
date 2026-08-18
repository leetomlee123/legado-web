"""EPUB 导入（zip + OPF 清单）。"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path, PurePosixPath

from book import insert_book_and_chapters

RE_SCRIPT = re.compile(r"(?is)<script[\s\S]*?</script>")
RE_STYLE = re.compile(r"(?is)<style[\s\S]*?</style>")
RE_BR = re.compile(r"(?i)<br\s*/?>")
RE_P = re.compile(r"(?i)</p>")
RE_DIV = re.compile(r"(?i)</div>")
RE_TAG = re.compile(r"<[^>]+>")
RE_NEWLINES = re.compile(r"\n{3,}")
RE_FULL_PATH = re.compile(r'full-path="([^"]+)"')
RE_DC_TITLE = re.compile(r"(?i)<dc:title[^>]*>([^<]+)</dc:title>")
RE_DC_CREATOR = re.compile(r"(?i)<dc:creator[^>]*>([^<]+)</dc:creator>")
RE_COVER_META = re.compile(r'(?i)<meta\s+name="cover"\s+content="([^"]+)"')
RE_ITEMREF = re.compile(r'<itemref\s+[^>]*idref="([^"]+)"')
RE_ITEM = re.compile(r'<item\s+[^>]*id="([^"]+)"[^>]*href="([^"]+)"')
RE_ITEM_ALT = re.compile(r'<item\s+[^>]*href="([^"]+)"[^>]*id="([^"]+)"')


def html_to_text(html: str) -> str:
    s = RE_SCRIPT.sub("", html)
    s = RE_STYLE.sub("", s)
    s = RE_BR.sub("\n", s)
    s = RE_P.sub("\n", s)
    s = RE_DIV.sub("\n", s)
    s = RE_TAG.sub("", s)
    s = (
        s.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    s = RE_NEWLINES.sub("\n\n", s)
    return s.strip()


def _zip_entry(names: list[str], name: str) -> str | None:
    want = str(PurePosixPath(name.replace("\\", "/")))
    for n in names:
        if str(PurePosixPath(n)) == want:
            return n
    return None


def import_epub_file(file_path: str, original_name: str) -> dict:
    try:
        zf = zipfile.ZipFile(file_path)
    except zipfile.BadZipFile as e:
        raise ValueError(f"无效的 EPUB：{e}") from e

    names = zf.namelist()
    container_name = _zip_entry(names, "META-INF/container.xml")
    if not container_name:
        raise ValueError("无效的 EPUB：缺少 container.xml")
    container_xml = zf.read(container_name).decode("utf-8", errors="replace")

    opf_path = "OEBPS/content.opf"
    m = RE_FULL_PATH.search(container_xml)
    if m:
        opf_path = m.group(1)

    opf_name = _zip_entry(names, opf_path)
    if not opf_name:
        raise ValueError("无效的 EPUB：缺少 OPF 清单")
    opf_xml = zf.read(opf_name).decode("utf-8", errors="replace")

    name = Path(original_name).stem
    tm = RE_DC_TITLE.search(opf_xml)
    if tm and tm.group(1).strip():
        name = tm.group(1).strip()
    author = ""
    cm = RE_DC_CREATOR.search(opf_xml)
    if cm:
        author = cm.group(1).strip()

    cover = ""
    cov = RE_COVER_META.search(opf_xml)
    if cov:
        id_attr = cov.group(1)
        href_re = re.compile(rf'id="{re.escape(id_attr)}"[^>]*href="([^"]+)"')
        hm = href_re.search(opf_xml)
        if hm:
            cover = hm.group(1)
        else:
            href_re2 = re.compile(rf'href="([^"]+)"[^>]*id="{re.escape(id_attr)}"')
            hm = href_re2.search(opf_xml)
            if hm:
                cover = hm.group(1)

    itemrefs = RE_ITEMREF.findall(opf_xml)
    manifest: dict[str, str] = {}
    for iid, href in RE_ITEM.findall(opf_xml):
        manifest[iid] = href
    for href, iid in RE_ITEM_ALT.findall(opf_xml):
        manifest.setdefault(iid, href)

    opf_dir = str(PurePosixPath(opf_path).parent)
    if opf_dir == ".":
        opf_dir = ""

    chapters: list[dict] = []
    for ir in itemrefs:
        href = manifest.get(ir)
        if not href:
            continue
        f_path = str(PurePosixPath(opf_dir) / href) if opf_dir else href
        f_path = str(PurePosixPath(f_path))
        entry = _zip_entry(names, f_path)
        if not entry:
            continue
        html = zf.read(entry).decode("utf-8", errors="replace")
        content = html_to_text(html)
        title = f"章节 {len(chapters) + 1}"
        for line in content.split("\n"):
            line = line.strip()
            if line and len(line) < 40:
                title = line
                content = content.replace(line, "", 1).strip()
                break
        if content or title:
            chapters.append({"title": title, "content": content})

    zf.close()
    if not chapters:
        raise ValueError("EPUB 中没有可读取的章节")

    if cover and not cover.startswith("http"):
        cover = str(PurePosixPath(opf_dir) / cover) if opf_dir else cover
        cover = str(PurePosixPath(cover))

    book_id = insert_book_and_chapters(name, author, cover, "epub", file_path, chapters)
    return {
        "success": 1,
        "bookId": book_id,
        "chapterCount": len(chapters),
        "cover": cover,
    }
