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


def _fill_native_search(out: SourceRule, raw: dict) -> None:
    search = out.search or SearchRule()
    search_url = _s(raw.get("searchUrl"))
    if "," in search_url:
        search_url = search_url.split(",", 1)[0]
    if not search.url:
        search.url = search_url

    rs = raw.get("ruleSearch")
    if isinstance(rs, dict):
        search.selector = search.selector or _s(rs.get("bookList"))
        search.book_url = search.book_url or _s(rs.get("bookUrl"))
        search.name = search.name or _s(rs.get("name"))
        search.author = search.author or _s(rs.get("author"))
        search.cover = search.cover or _s(rs.get("coverUrl"))
        search.intro = search.intro or _s(rs.get("intro"))

    sub = raw.get("search")
    if isinstance(sub, dict):
        search.url = search.url or _s(raw.get("searchUrl")) or _s(sub.get("url"))
        search.selector = search.selector or _s(sub.get("selector"))
        search.book_url = search.book_url or _s(sub.get("bookUrl"))
        search.name = search.name or _s(sub.get("name"))
        search.author = search.author or _s(sub.get("author"))
        search.cover = search.cover or _s(sub.get("cover"))
        search.intro = search.intro or _s(sub.get("intro"))

    if search.url or search.selector:
        out.search = search


def _fill_native_detail(out: SourceRule, raw: dict) -> None:
    if out.detail is not None:
        return
    rbi = raw.get("ruleBookInfo")
    if not isinstance(rbi, dict):
        return
    intro = _s(rbi.get("intro"))
    author = _s(rbi.get("author"))
    cover = _s(rbi.get("coverUrl") or rbi.get("cover"))
    if intro or author or cover:
        out.detail = DetailRule(intro=intro, author=author, cover=cover)


def _fill_native_toc(out: SourceRule, raw: dict) -> None:
    if out.toc is not None and out.toc.selector:
        return
    rt = raw.get("ruleToc")
    if not isinstance(rt, dict):
        return
    selector = _s(rt.get("chapterList") or rt.get("selector"))
    if not selector:
        return
    toc_url = ""
    rbi = raw.get("ruleBookInfo")
    if isinstance(rbi, dict):
        toc_url = _s(rbi.get("tocUrl"))
    out.toc = TocRule(
        url=toc_url,
        selector=selector,
        title=_s(rt.get("chapterName") or rt.get("title")),
        chapter_url=_s(rt.get("chapterUrl")),
    )


def _fill_native_content(out: SourceRule, raw: dict) -> None:
    if out.content is not None and out.content.selector:
        return
    rc = raw.get("ruleContent")
    if not isinstance(rc, dict):
        return
    content_rule = _s(rc.get("content") or rc.get("selector"))
    if not content_rule:
        return
    selector, text = content_rule, _s(rc.get("text")) or "text"
    if "@" in content_rule:
        selector, attr = content_rule.rsplit("@", 1)
        selector, text = selector.strip(), attr.strip() or "text"
    out.content = ContentRule(selector=selector.strip(), text=text)


def parse_legado_rule(s: str) -> SourceRule | None:
    """同时理解本应用简版规则和阅读 3.0 原生订阅格式。"""
    if not (s or "").strip():
        return None
    try:
        raw = json.loads(s)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict):
        return None

    out = parse_rule(s) or SourceRule()
    _fill_native_search(out, raw)
    _fill_native_detail(out, raw)
    _fill_native_toc(out, raw)
    _fill_native_content(out, raw)

    if out.search is None and out.toc is None and out.content is None:
        return None
    return out


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


def normalize_extract_rule(rule: str, default: str) -> str:
    """把 `href` / `src` 补成 `@href`，避免被当成 CSS 选择器。"""
    r = (rule or "").strip()
    if not r:
        return default
    if r in ("href", "src", "text", "html", "ownText", "textNodes") and "@" not in r:
        return f"@{r}" if r in ("href", "src") else r
    return r


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
    book_url_rule = normalize_extract_rule(rule.book_url, "a@href")
    root = soup if isinstance(soup, Tag) else soup
    for s in safe_select(root, rule.selector):
        try:
            items.append(
                {
                    "name": extract_value(s, _or_default(rule.name, "text"), base_url),
                    "author": extract_value(s, rule.author, base_url),
                    "cover": extract_value(s, rule.cover, base_url),
                    "intro": extract_value(s, rule.intro, base_url),
                    "bookUrl": extract_value(s, book_url_rule, base_url),
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
                "chapterUrl": extract_value(
                    s, normalize_extract_rule(rule.chapter_url, "@href"), base_url
                ),
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


def _rule_for_source(src: dict) -> SourceRule:
    rule = parse_legado_rule(src.get("rule") or "")
    if rule is None:
        raise ValueError("书源规则无效")
    return rule


def _toc_url(book: dict, rule: SourceRule) -> str:
    raw = (rule.toc.url if rule.toc else "") or ""
    book_url = book.get("source_url") or ""
    if raw:
        raw = raw.replace("{{bookUrl}}", book_url).replace("{bookUrl}", book_url)
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
    return book_url


def refresh_web_chapters(book: dict) -> None:
    src = source_by_id(int(book.get("source_id") or 0))
    if not src:
        raise ValueError("无书源")
    rule = _rule_for_source(src)
    if rule.toc is None or not rule.toc.selector:
        raise ValueError("无目录规则")
    toc_url = _toc_url(book, rule)
    if not toc_url:
        raise ValueError("缺少书籍地址")
    html = fetch_url(toc_url)
    toc = crawl_toc(html, rule.toc, toc_url)
    if not toc:
        return
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
    rule = _rule_for_source(src)
    if rule.content is None:
        raise ValueError("无内容规则")
    target = chapter_url or book.get("source_url") or ""
    html = fetch_url(target)
    return crawl_content(html, rule.content)


def crawl_book_detail(book: dict) -> DetailRule:
    src = source_by_id(int(book.get("source_id") or 0))
    if not src:
        raise ValueError("无书源")
    rule = _rule_for_source(src)
    if rule.detail is None:
        raise ValueError("无详情规则")
    html = fetch_url(book.get("source_url") or "")
    return crawl_detail(html, rule.detail, book.get("source_url") or "")
