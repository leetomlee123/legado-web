"""书源规则引擎：阅读 3.0 / 简版规则解析与抓取。

网络请求统一走 curl_cffi，以 Chrome TLS 指纹绕过常见站点反爬。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from curl_cffi import requests as cffi_requests

from db import require_db
from settings import get_proxy

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def fetch_url(url: str, timeout: float = 20) -> str:
    resp = cffi_requests.get(
        url,
        impersonate="chrome120",
        timeout=timeout,
        headers={"User-Agent": UA},
        allow_redirects=True,
        proxy=get_proxy() or None,
    )
    resp.raise_for_status()
    # curl_cffi 已按 Content-Type / charset 解码；必要时回退
    text = resp.text or ""
    if not text and resp.content:
        try:
            text = resp.content.decode("utf-8")
        except UnicodeDecodeError:
            text = resp.content.decode("gb18030", errors="replace")
    return text


@dataclass
class SearchRule:
    url: str = ""
    selector: str = ""
    name: str = ""
    author: str = ""
    cover: str = ""
    intro: str = ""
    book_url: str = ""


@dataclass
class DetailRule:
    intro: str = ""
    author: str = ""
    cover: str = ""


@dataclass
class TocRule:
    url: str = ""
    selector: str = ""
    title: str = ""
    chapter_url: str = ""


@dataclass
class ContentRule:
    selector: str = ""
    text: str = ""


@dataclass
class SourceRule:
    search: SearchRule | None = None
    detail: DetailRule | None = None
    toc: TocRule | None = None
    content: ContentRule | None = None


def _s(v: Any) -> str:
    return v if isinstance(v, str) else ""


def parse_rule(s: str) -> SourceRule | None:
    if not (s or "").strip():
        return None
    try:
        raw = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None
    out = SourceRule()
    if isinstance(raw.get("search"), dict):
        sub = raw["search"]
        out.search = SearchRule(
            url=_s(sub.get("url") or sub.get("searchUrl") or sub.get("ruleUrl")),
            selector=_s(sub.get("selector") or sub.get("bookList") or sub.get("searchSelector")),
            name=_s(sub.get("name")),
            author=_s(sub.get("author")),
            cover=_s(sub.get("cover") or sub.get("coverUrl")),
            intro=_s(sub.get("intro")),
            book_url=_s(sub.get("bookUrl")),
        )
    if isinstance(raw.get("detail"), dict):
        sub = raw["detail"]
        out.detail = DetailRule(
            intro=_s(sub.get("intro")),
            author=_s(sub.get("author")),
            cover=_s(sub.get("cover")),
        )
    if isinstance(raw.get("toc"), dict):
        sub = raw["toc"]
        out.toc = TocRule(
            url=_s(sub.get("url")),
            selector=_s(sub.get("selector")),
            title=_s(sub.get("title")),
            chapter_url=_s(sub.get("chapterUrl")),
        )
    if isinstance(raw.get("content"), dict):
        sub = raw["content"]
        out.content = ContentRule(
            selector=_s(sub.get("selector")),
            text=_s(sub.get("text")),
        )
    return out


def parse_legado_rule(s: str) -> SourceRule | None:
    """同时理解本应用简版规则和阅读 3.0 原生订阅格式。"""
    r = parse_rule(s)
    if r is not None and r.search is not None:
        return r
    try:
        raw = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None

    search = SearchRule()
    search_url = _s(raw.get("searchUrl"))
    if "," in search_url:
        search_url = search_url.split(",", 1)[0]
    search.url = search_url

    rs = raw.get("ruleSearch")
    if isinstance(rs, dict):
        if _s(rs.get("bookList")):
            search.selector = _s(rs.get("bookList"))
        search.book_url = _s(rs.get("bookUrl"))
        search.name = _s(rs.get("name"))
        search.author = _s(rs.get("author"))
        search.cover = _s(rs.get("coverUrl"))
        search.intro = _s(rs.get("intro"))

    sub = raw.get("search")
    if isinstance(sub, dict):
        if not search.url:
            search.url = _s(raw.get("searchUrl")) or _s(sub.get("url"))
        if not search.selector:
            search.selector = _s(sub.get("selector"))
        if not search.book_url:
            search.book_url = _s(sub.get("bookUrl"))
        if not search.name:
            search.name = _s(sub.get("name"))
        if not search.author:
            search.author = _s(sub.get("author"))
        if not search.cover:
            search.cover = _s(sub.get("cover"))
        if not search.intro:
            search.intro = _s(sub.get("intro"))

    if not search.url or not search.selector:
        return None
    return SourceRule(search=search)


def split_legado_rules(name: str, text: str) -> list[tuple[str, str]]:
    try:
        arr = json.loads(text)
    except json.JSONDecodeError:
        return [(name, text)]
    if not isinstance(arr, list) or not arr:
        return [(name, text)]
    out: list[tuple[str, str]] = []
    for it in arr:
        if not isinstance(it, dict):
            continue
        nm = _s(it.get("bookSourceName")) or name or "书源"
        out.append((nm, json.dumps(it, ensure_ascii=False)))
    return out or [(name, text)]


def legado_rule_insert(name: str, rule: str) -> int:
    conn = require_db()
    now = int(time.time() * 1000)
    cur = conn.execute(
        "INSERT INTO book_source (name, url, rule, create_time) VALUES (?, '', ?, ?)",
        (name, rule, now),
    )
    conn.commit()
    return int(cur.lastrowid)


def abs_url(base: str, href: str) -> str:
    href = (href or "").strip()
    if not href:
        return ""
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not base:
        return href
    return urljoin(base, href)


def _or_default(s: str, d: str) -> str:
    return d if not (s or "").strip() else s


# --- 阅读3.0 (jsoup) 选择器支持 ---
#
# 书源规则使用 jsoup 语法，与标准 CSS 有两处差异需要兼容：
#   1. `.info_box.1`：最后的数字是“第几个匹配元素”的位置下标（不是 class 名）
#   2. `X##正则##替换`：对取到的文本做正则替换/截断


_JS_POS = re.compile(r"\.(\d{1,2})\s*$")  # 行尾 `.N` 位置下标


def _strip_js_pos(selector: str) -> tuple[str, int | None]:
    """若选择器末尾是 `.N` 位置下标，返回 (基础选择器, N)。"""
    m = _JS_POS.search((selector or "").strip())
    if m:
        base = (selector[: m.start()]).strip()
        return base, int(m.group(1))
    return selector, None


def safe_select(el: Tag, selector: str) -> list[Tag]:
    if not (selector or "").strip():
        return []
    try:
        return list(el.select(selector))
    except Exception:
        return []


def safe_select_one(el: Tag, selector: str) -> Tag | None:
    if not (selector or "").strip():
        return None
    base, pos = _strip_js_pos(selector)
    found = safe_select(el, base)
    if not found:
        return None
    if pos is not None:
        # jsoup 位置下标从 1 开始；越界取两端
        if 1 <= pos <= len(found):
            return found[pos - 1]
        return found[0] if pos == 1 else None
    return found[0]


def safe_select_one(el: Tag, selector: str) -> Tag | None:
    if not (selector or "").strip():
        return None
    base, pos = _strip_js_pos(selector)
    found = safe_select(el, base)
    if not found:
        return None
    if pos is not None:
        # jsoup 位置下标从 1 开始；越界取两端
        if 1 <= pos <= len(found):
            return found[pos - 1]
        return found[0] if pos == 1 else None
    return found[0]


def extract_value(el: Tag | None, rule: str, base_url: str) -> str:
    if el is None:
        return ""
    rule = (rule or "").strip()
    if not rule:
        return ""

    def _attr(target: Tag, attr: str) -> str:
        attr = attr.split("##")[0].strip()  # strip ## part for attr name
        if attr in ("text", "textN", "textNodes", "ownText"):
            return target.get_text(separator="", strip=True)
        if attr == "html":
            return "".join(str(c) for c in target.contents).strip()
        v = target.get(attr) or ""
        if isinstance(v, list):
            v = v[0] if v else ""
        return abs_url(base_url, str(v).strip())

    # 处理 @attr + ## 替换
    if "@" in rule:
        css, attr = rule.rsplit("@", 1)
        css, attr = css.strip(), attr.strip()
        target: Tag | None = el
        if css:
            target = safe_select_one(el, css)
        if target is None:
            return ""
        text = _attr(target, attr)

        # 处理 ## 替换规则
        if "##" in rule:
            parts = rule.split("##")
            if len(parts) >= 3:
                regex, repl = parts[1], parts[2]
                text = re.sub(regex, repl, text)
            elif len(parts) == 2:
                regex = parts[1]
                text = re.split(regex, text, 1)[0]

        return text

    # fallback
    if rule in ("text", "textN", "textNodes", "ownText"):
        return el.get_text(separator="", strip=True)
    if rule == "html":
        return "".join(str(c) for c in el.contents).strip()

    # 普通 CSS 选择器 fallback
    found = safe_select_one(el, rule)
    return found.get_text(separator="", strip=True) if found is not None else ""


def crawl_search(html: str, rule: SearchRule | None, base_url: str) -> list[dict]:
    if rule is None or not rule.selector:
        return []
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    book_url_rule = rule.book_url or rule.url
    root = soup if isinstance(soup, Tag) else soup
    for s in safe_select(root, rule.selector):
        try:
            items.append(
                {
                    "name": extract_value(s, _or_default(rule.name, "text"), base_url),
                    "author": extract_value(s, rule.author, base_url),
                    "cover": extract_value(s, rule.cover, base_url),
                    "intro": extract_value(s, rule.intro, base_url),
                    "bookUrl": extract_value(s, _or_default(book_url_rule, "a@href"), base_url),
                }
            )
        except Exception:
            continue
    return items


def crawl_detail(html: str, rule: DetailRule | None, base_url: str) -> DetailRule:
    out = DetailRule()
    if rule is None:
        return out
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body") or soup
    if not isinstance(body, Tag):
        return out
    if rule.intro:
        out.intro = extract_value(body, rule.intro, base_url)
    if rule.author:
        out.author = extract_value(body, rule.author, base_url)
    if rule.cover:
        out.cover = extract_value(body, rule.cover, base_url)
    return out


def crawl_toc(html: str, rule: TocRule | None, base_url: str) -> list[dict]:
    if rule is None or not rule.selector:
        return []
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    root = soup if isinstance(soup, Tag) else soup
    for s in safe_select(root, rule.selector):
        out.append(
            {
                "title": extract_value(s, _or_default(rule.title, "text"), base_url),
                "chapterUrl": extract_value(s, _or_default(rule.chapter_url, "@href"), base_url),
            }
        )
    return out


def crawl_content(html: str, rule: ContentRule | None) -> str:
    if rule is None:
        return html
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    if not rule.selector:
        return soup.get_text(separator="\n", strip=True)
    root = soup if isinstance(soup, Tag) else soup
    el = safe_select_one(root, rule.selector)
    return extract_value(el, _or_default(rule.text, "text"), "")


def source_by_id(sid: int) -> dict | None:
    conn = require_db()
    row = conn.execute(
        "SELECT id, name, url, enabled, rule, create_time FROM book_source WHERE id=?",
        (sid,),
    ).fetchone()
    return dict(row) if row else None


def refresh_web_chapters(book: dict) -> None:
    src = source_by_id(int(book.get("source_id") or 0))
    if not src:
        raise ValueError("无书源")
    rule = parse_rule(src.get("rule") or "")
    if rule is None or rule.toc is None:
        raise ValueError("无目录规则")
    html = fetch_url(book.get("source_url") or "")
    toc = crawl_toc(html, rule.toc, book.get("source_url") or "")
    conn = require_db()
    conn.execute("DELETE FROM chapter WHERE book_id=?", (book["id"],))
    conn.executemany(
        "INSERT INTO chapter (book_id, title, idx, content_url) VALUES (?, ?, ?, ?)",
        [(book["id"], c["title"], i, c["chapterUrl"]) for i, c in enumerate(toc)],
    )
    conn.commit()


def fetch_web_chapter(book: dict, chapter_url: str) -> str:
    src = source_by_id(int(book.get("source_id") or 0))
    if not src:
        raise ValueError("无书源")
    rule = parse_rule(src.get("rule") or "")
    if rule is None or rule.content is None:
        raise ValueError("无内容规则")
    target = chapter_url or book.get("source_url") or ""
    html = fetch_url(target)
    return crawl_content(html, rule.content)


def crawl_book_detail(book: dict) -> DetailRule:
    src = source_by_id(int(book.get("source_id") or 0))
    if not src:
        raise ValueError("无书源")
    rule = parse_rule(src.get("rule") or "")
    if rule is None or rule.detail is None:
        raise ValueError("无详情规则")
    html = fetch_url(book.get("source_url") or "")
    return crawl_detail(html, rule.detail, book.get("source_url") or "")
