"""书源规则引擎：阅读 3.0 / 简版规则解析与抓取。

网络请求统一走 curl_cffi，以 Chrome TLS 指纹绕过常见站点反爬。
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any
import urllib.parse
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from curl_cffi import requests as cffi_requests

from db import require_db
from settings import (
    get_proxy,
    normalize_source_url,
    get_m_to_www,
    convert_m_to_www,
    convert_www_to_m,
)
from logger import get_logger

logger = get_logger("source")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def decode_http_response(resp) -> str:
    content = resp.content or b""
    if not content:
        return ""
    head_sample = content[:2048].lower()
    if b"charset=gbk" in head_sample or b"charset=\"gbk\"" in head_sample or b"charset='gbk'" in head_sample:
        return content.decode("gbk", errors="replace")
    if b"charset=gb2312" in head_sample or b"charset=\"gb2312\"" in head_sample:
        return content.decode("gb2312", errors="replace")
    if b"charset=gb18030" in head_sample or b"charset=\"gb18030\"" in head_sample:
        return content.decode("gb18030", errors="replace")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("gb18030", errors="replace")


def fetch_url(url: str, timeout: float = 20, base_url: str = "", context: str = "") -> str:
    t0 = time.perf_counter()
    url = (url or "").strip()
    if base_url:
        if not (url.startswith("http://") or url.startswith("https://")):
            url = urljoin(base_url, url)
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"无效的请求地址: {url}")

    # 构建主选与回退候选地址列表
    candidates = [url]
    if get_m_to_www():
        converted_www = convert_m_to_www(url)
        if converted_www != url:
            # 原始为 m. 网址，首选 www. 桌面端，保底回退原始 m. 移动端
            candidates = [converted_www, url]
        else:
            converted_m = convert_www_to_m(url)
            if converted_m != url:
                # 原始已是 www. 网址，首选 www.，保底回退 m.
                candidates = [url, converted_m]

    ctx_label = f"[{context}] " if context else ""
    last_err = None

    for idx, cand_url in enumerate(candidates):
        is_fallback = idx > 0
        if is_fallback:
            logger.warning(
                "%s[域名回退] 尝试 www. 域名失败，自动回退至移动端 (m.) 发起请求 -> %s",
                ctx_label,
                cand_url,
            )
        else:
            logger.info("%s发起 GET 网络请求: %s (超时: %ds)", ctx_label, cand_url, int(timeout))

        try:
            resp = cffi_requests.get(
                cand_url,
                impersonate="chrome120",
                timeout=timeout,
                headers={"User-Agent": UA},
                allow_redirects=True,
                proxy=get_proxy() or None,
                verify=False,
            )
            resp.raise_for_status()
            html = decode_http_response(resp)

            # 404 / 页面不存在防错检测（部分站点 404 仍返回 HTTP 200 短 HTML）
            if (
                len(candidates) > 1
                and idx == 0
                and len(html) < 2000
                and any(err_kw in html for err_kw in ["404 Not Found", "页面不存在", "404 错误", "找不到页面", "章节不存在"])
            ):
                logger.warning(
                    "%s[域名回退] www. 页面返回 404 错误提示页 (大小 %d 字节)，自动回退至移动端...",
                    ctx_label,
                    len(html),
                )
                continue

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            logger.info(
                "%sGET 请求成功%s: 状态码 %d, 耗时 %dms, 响应大小 %d 字节, 最终URL: %s",
                ctx_label,
                " (域名回退成功)" if is_fallback else "",
                resp.status_code,
                elapsed_ms,
                len(resp.content or b""),
                str(resp.url or cand_url),
            )
            return html
        except Exception as e:
            last_err = e
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning(
                "%sGET 请求失败%s: %s (耗时 %dms, URL: %s)",
                ctx_label,
                " (www. 域名首选尝试)" if len(candidates) > 1 and idx == 0 else "",
                e,
                elapsed_ms,
                cand_url,
            )
            if len(candidates) > 1 and idx == 0:
                continue

    if last_err:
        raise last_err
    raise ValueError(f"请求失败: {url}")


def fetch_subscription_url(url: str, timeout: float = 30) -> tuple[str, int]:
    """
    获取书源订阅内容，自动测算下载耗时（ms），并针对海外 Github/Gitlab 源提供国内镜像加速回退。
    返回 (html_or_json_text, elapsed_ms)。
    """
    t0 = time.perf_counter()
    url = (url or "").strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"无效的订阅 URL: {url}")

    candidates = [url]
    if "raw.githubusercontent.com" in url:
        candidates.append(f"https://ghproxy.net/{url}")
        candidates.append(f"https://raw.gitmirror.com/{url.replace('https://raw.githubusercontent.com/', '')}")

    last_err = None
    for cand in candidates:
        try:
            resp = cffi_requests.get(
                cand,
                impersonate="chrome120",
                timeout=timeout,
                headers={"User-Agent": UA},
                allow_redirects=True,
                proxy=get_proxy() or None,
                verify=False,
            )
            if resp.status_code < 400:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                return decode_http_response(resp), elapsed_ms
        except Exception as e:
            last_err = e

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    if last_err:
        raise last_err
    raise ValueError("下载书源订阅失败")


def test_source_latency(
    src_id: int,
    name: str,
    url: str,
    rule_str: str,
    timeout: float = 8,
    proxy: str = "",
) -> dict:
    """探测书源响应延迟（毫秒）。"""
    t0 = time.perf_counter()
    target_url = (url or "").strip()

    # 优先使用 searchUrl 或 bookSourceUrl
    if rule_str:
        try:
            rule = parse_legado_rule(rule_str)
            if rule and rule.search and rule.search.url:
                spec = extract_legado_search_url_spec(rule.search.url, rule.base_url or target_url)
                if spec:
                    raw_u = spec.split(",", 1)[0].strip()
                    raw_u = _replace_key(raw_u, "1")
                    if raw_u.startswith("http://") or raw_u.startswith("https://"):
                        target_url = raw_u
                    elif rule.base_url:
                        target_url = urljoin(rule.base_url, raw_u)
        except Exception:
            pass

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        target_url = (url or "").strip()

    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        return {
            "sourceId": src_id,
            "sourceName": name,
            "success": False,
            "delay": -1,
            "error": "无有效目标网址",
        }

    try:
        active_proxy = proxy or get_proxy() or None
        resp = cffi_requests.get(
            target_url,
            impersonate="chrome120",
            timeout=timeout,
            headers={"User-Agent": UA},
            allow_redirects=True,
            proxy=active_proxy,
            verify=False,
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "sourceId": src_id,
            "sourceName": name,
            "success": resp.status_code < 400,
            "delay": elapsed_ms,
            "status": resp.status_code,
            "error": None if resp.status_code < 400 else f"HTTP {resp.status_code}",
        }
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "sourceId": src_id,
            "sourceName": name,
            "success": False,
            "delay": elapsed_ms,
            "error": str(e),
        }


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
    next_toc_url: str = ""


@dataclass
class ContentRule:
    selector: str = ""
    text: str = ""
    next_content_url: str = ""
    replace_regex: str = ""
    web_js: str = ""


@dataclass
class SourceRule:
    base_url: str = ""
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
            next_toc_url=_s(sub.get("nextTocUrl") or sub.get("nextUrl")),
        )
    if isinstance(raw.get("content"), dict):
        sub = raw["content"]
        out.content = ContentRule(
            selector=_s(sub.get("selector")),
            text=_s(sub.get("text")),
            next_content_url=_s(sub.get("nextContentUrl") or sub.get("nextUrl")),
            replace_regex=_s(sub.get("replaceRegex")),
            web_js=_s(sub.get("webJs")),
        )
    return out


def _fill_native_search(out: SourceRule, raw: dict) -> None:
    search = out.search or SearchRule()
    search_url = _s(raw.get("searchUrl"))
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
        next_toc_url=_s(rt.get("nextTocUrl")),
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
    out.content = ContentRule(
        selector=selector.strip(),
        text=text,
        next_content_url=_s(rc.get("nextContentUrl")),
        replace_regex=_s(rc.get("replaceRegex")),
        web_js=_s(rc.get("webJs")),
    )


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
    out.base_url = _s(raw.get("bookSourceUrl") or raw.get("sourceUrl") or raw.get("url") or raw.get("host") or "").strip()
    _fill_native_search(out, raw)
    _fill_native_detail(out, raw)
    _fill_native_toc(out, raw)
    _fill_native_content(out, raw)

    if out.search is None and out.toc is None and out.content is None:
        return None
    return out


def _extract_source_item(it: dict, default_name: str = "") -> tuple[str, str, str] | None:
    if not isinstance(it, dict):
        return None
    nm = (
        _s(it.get("bookSourceName"))
        or _s(it.get("sourceName"))
        or _s(it.get("name"))
        or _s(it.get("title"))
        or default_name
        or "书源"
    )
    u = (
        _s(it.get("bookSourceUrl"))
        or _s(it.get("sourceUrl"))
        or _s(it.get("url"))
        or _s(it.get("searchUrl"))
        or _s(it.get("sortUrl"))
    )
    return (nm, u, json.dumps(it, ensure_ascii=False))


def parse_sources_from_payload(text: str, default_name: str = "") -> list[tuple[str, str, str]]:
    """
    智能解析任意形式的书源载荷（JSON 数组、单对象、HTML 页面中的嵌入 JSON 或链接）。
    返回列表：[(name, source_url, rule_json_str)]
    """
    text = (text or "").strip()
    if not text:
        return []

    # 1. 尝试直接解析标准 JSON
    try:
        data = json.loads(text)
        if isinstance(data, list):
            out = []
            for it in data:
                item = _extract_source_item(it, default_name)
                if item:
                    out.append(item)
            if out:
                return out
        elif isinstance(data, dict):
            item = _extract_source_item(data, default_name)
            if item:
                return [item]
    except json.JSONDecodeError:
        pass

    # 2. 如果包含 HTML/文本，使用正则提取其中嵌套的 JSON 数组/对象
    out = []
    # 查找 [ { ... "sourceName" / "bookSourceName" ... } ] 结构
    json_array_matches = re.findall(r"\[\s*\{.*?(?:\"bookSourceName\"|\"sourceName\"|\"ruleSearch\").*?\}\s*\]", text, re.DOTALL)
    for block in json_array_matches:
        try:
            arr = json.loads(block)
            if isinstance(arr, list):
                for it in arr:
                    item = _extract_source_item(it, default_name)
                    if item:
                        out.append(item)
        except Exception:
            continue

    if out:
        return out

    # 3. 查找单个 { "bookSourceName" / "sourceName": ... } 对象
    json_obj_matches = re.findall(r"\{[^{}]*(?:\"bookSourceName\"|\"sourceName\"|\"ruleSearch\")[^{}]*\}", text, re.DOTALL)
    for block in json_obj_matches:
        try:
            obj = json.loads(block)
            item = _extract_source_item(obj, default_name)
            if item:
                out.append(item)
        except Exception:
            continue

    return out or [(default_name or "自定义书源", "", text)]


def split_legado_rules(name: str, text: str) -> list[tuple[str, str]]:
    sources = parse_sources_from_payload(text, name)
    return [(s[0], s[2]) for s in sources]


def legado_rule_upsert(name: str, source_url: str, rule: str) -> tuple[int, bool]:
    """
    智能去重更新或插入书源：
    如果存在同名或同 URL 的书源，则更新规则；否则插入新书源。
    返回: (source_id, is_new_insert)
    """
    conn = require_db()
    now = int(time.time() * 1000)

    # 优先根据 url 匹配，其次根据 name 匹配
    existing = None
    if source_url:
        existing = conn.execute("SELECT id FROM book_source WHERE url=?", (source_url,)).fetchone()
    if not existing and name:
        existing = conn.execute("SELECT id FROM book_source WHERE name=?", (name,)).fetchone()

    if existing:
        sid = int(existing["id"])
        conn.execute(
            "UPDATE book_source SET name=?, url=?, rule=?, enabled=1 WHERE id=?",
            (name, source_url, rule, sid),
        )
        conn.commit()
        return sid, False

    cur = conn.execute(
        "INSERT INTO book_source (name, url, rule, enabled, create_time) VALUES (?, ?, ?, 1, ?)",
        (name, source_url, rule, now),
    )
    conn.commit()
    return int(cur.lastrowid), True


def legado_rule_insert(name: str, rule: str) -> int:
    sid, _ = legado_rule_upsert(name, "", rule)
    return sid


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


def convert_jsoup_to_css(sel: str) -> str:
    """把 Legado jsoup 语法转为标准 CSS 选择器（tag.xxx -> xxx, class.xxx -> .xxx, id.xxx -> #xxx）。"""
    s = (sel or "").strip()
    if not s:
        return ""
    # 处理 class.name1 name2 name3 包含空格的多类名
    s = re.sub(
        r"(?:^|[\s>+~,])class\.([a-zA-Z0-9_\-\s]+?)(?=[>+~,\.\[\:]|$)",
        lambda m: "." + ".".join(m.group(1).split()),
        s,
    )
    s = re.sub(r"(?:^|[\s>+~,])tag\.([a-zA-Z0-9_\-]+)", lambda m: m.group(0).replace("tag.", ""), s)
    s = re.sub(r"(?:^|[\s>+~,])id\.([a-zA-Z0-9_\-]+)", lambda m: m.group(0).replace("id.", "#"), s)
    return s.strip()


def _strip_js_pos_and_slice(selector: str) -> tuple[str, int | None, tuple[int | None, int | None] | None, int | None]:
    """
    处理 Legado 3.0 选择器末尾的位置下标、切片与排除：
    例如：
      .author.0        -> ('.author', 0, None, None)
      div#info > p.0   -> ('div#info > p', 0, None, None)
      div.con_top > a.1-> ('div.con_top > a', 1, None, None)
      dd[9:]           -> ('dd', None, (9, None), None)
      dd[0]            -> ('dd', 0, None, None)
      p!0              -> ('p', None, None, 0) # 排除第0项
      li!-1            -> ('li', None, None, -1) # 排除最后一项
    """
    s = (selector or "").strip()
    if not s:
        return "", None, None, None

    # 1. 检查 !N 排除语法
    excl_m = re.search(r"!(-?\d+)\s*$", s)
    if excl_m:
        base = s[: excl_m.start()].strip()
        return base, None, None, int(excl_m.group(1))

    # 2. 检查方括号切片 [9:] 或 [0]
    slice_m = re.search(r"\[(-?\d*):?(-?\d*)\]\s*$", s)
    if slice_m:
        base = s[: slice_m.start()].strip()
        s1, s2 = slice_m.group(1), slice_m.group(2)
        if ":" in slice_m.group(0):
            start = int(s1) if s1 else None
            stop = int(s2) if s2 else None
            return base, None, (start, stop), None
        else:
            return base, int(s1) if s1 else None, None, None

    # 3. 检查末尾 `.N` 或 `.-N`
    pos_m = re.search(r"\.(-?\d{1,3})\s*$", s)
    if pos_m:
        base = s[: pos_m.start()].strip()
        return base, int(pos_m.group(1)), None, None

    return s, None, None, None


def sanitize_css_selector(sel: str) -> str:
    """自动修复未加双引号的包含特殊符号的属性选择器（如 [href*=book/chapter] -> [href*="book/chapter"]）。"""
    if not (sel or "").strip():
        return ""
    def _fix_attr(m):
        attr_op = m.group(1)
        val = m.group(2).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            return f"[{attr_op}{val}]"
        return f'[{attr_op}"{val}"]'
    return re.sub(r'\[([a-zA-Z0-9_\-]+[*~|^$]?=)([^\]]+)\]', _fix_attr, sel)


def safe_select(el: Tag, selector: str) -> list[Tag]:
    if not (selector or "").strip() or el is None:
        return []
    selector = selector.strip()

    # 支持 || fallback 规则
    if "||" in selector:
        for part in selector.split("||"):
            res = safe_select(el, part.strip())
            if res:
                return res
        return []

    # 支持 && / %% 组合规则（拼接多个选择器的匹配结果）
    if "&&" in selector or "%%" in selector:
        parts = [p.strip() for p in re.split(r"&&|%%", selector) if p.strip()]
        out = []
        for p in parts:
            out.extend(safe_select(el, p))
        return out

    # 支持 @ 分层级联选择（例如 class.col-sm-6 chapter-list@a）
    if "@" in selector:
        segments = [s.strip() for s in selector.split("@") if s.strip()]
        current = [el]
        for seg in segments:
            next_nodes = []
            for node in current:
                next_nodes.extend(safe_select(node, seg))
            current = next_nodes
            if not current:
                break
        return current

    base, pos_idx, slice_args, excl_idx = _strip_js_pos_and_slice(selector)
    if not base:
        return [el]

    # 支持 text.关键词 伪选择器
    if base.startswith("text."):
        kw = base[5:].strip()
        matched = []
        for tag in el.find_all("a"):
            if kw in tag.get_text():
                matched.append(tag)
        if not matched:
            for tag in el.find_all():
                if kw in tag.get_text() and not any(kw in child.get_text() for child in tag.find_all()):
                    matched.append(tag)
        found = matched
    else:
        css_converted = convert_jsoup_to_css(base)
        sanitized_base = sanitize_css_selector(css_converted)
        try:
            found = list(el.select(sanitized_base))
        except Exception:
            try:
                found = list(el.select(base))
            except Exception:
                found = []

    if slice_args is not None:
        start, stop = slice_args
        return found[slice(start, stop)]

    if excl_idx is not None and found:
        if 0 <= excl_idx < len(found):
            found = [e for i, e in enumerate(found) if i != excl_idx]
        elif excl_idx < 0 and abs(excl_idx) <= len(found):
            idx = len(found) + excl_idx
            found = [e for i, e in enumerate(found) if i != idx]

    if pos_idx is not None and found:
        if 0 <= pos_idx < len(found):
            return [found[pos_idx]]
        elif pos_idx < 0 and abs(pos_idx) <= len(found):
            return [found[pos_idx]]
        return []

    return found


def safe_select_one(el: Tag, selector: str) -> Tag | None:
    found = safe_select(el, selector)
    return found[0] if found else None


def _parse_options_json(raw_json: str) -> dict:
    import ast
    raw_json = (raw_json or "").strip()
    if not raw_json:
        return {}
    try:
        return json.loads(raw_json)
    except Exception:
        pass
    try:
        val = ast.literal_eval(raw_json)
        if isinstance(val, dict):
            return val
    except Exception:
        pass
    return {}


def extract_legado_search_url_spec(spec: str, base_url: str = "") -> str:
    """从包含 @js: / <js> / 拼接语法的 searchUrl 中智能提取规范化的 search_spec。"""
    spec = (spec or "").strip()
    if not spec:
        return ""

    if "<js>" in spec:
        cleaned = re.sub(r"^<js>.*?</js>", "", spec, flags=re.DOTALL).strip()
        if cleaned:
            spec = cleaned
        else:
            m = re.search(r"['\"](https?://[^'\"]+|/[^'\"]+)['\"]", spec)
            if m:
                spec = m.group(1)
            else:
                spec = re.sub(r"</?js>", "", spec).strip()
                spec = re.sub(r";\s*result.*$", "", spec).strip()

    if spec.startswith("@js:"):
        js_code = spec[4:].strip()
        m_base = re.search(r'url\s*=\s*baseUrl\s*\+\s*["\'](.*?)(?:["\']\s*;|$)', js_code)
        if m_base:
            part = m_base.group(1).strip()
            if "," in part:
                p_url, p_opt = part.split(",", 1)
                spec = urljoin(base_url, p_url.strip()) + "," + p_opt.strip()
            else:
                spec = urljoin(base_url, part)
        else:
            m_url = re.search(r'url\s*=\s*["\'](https?://.*?|/.*?)(?:["\']\s*;|$)', js_code)
            if m_url:
                spec = m_url.group(1).strip()
            else:
                m_any = re.search(r'["\'](https?://.*?|/.*?)(?:["\']\s*;|$)', js_code)
                if m_any:
                    spec = m_any.group(1).strip()
                else:
                    m_http = re.search(r'(https?://[^\s`"\'\)]+)', js_code)
                    if m_http:
                        spec = m_http.group(1)

    return spec.strip()


def fetch_search_response(
    search_spec: str,
    keyword: str,
    timeout: int = 15,
    base_url: str = "",
    source_name: str = "",
    source_id: int | str = "",
) -> tuple[str, str]:
    """
    支持 Legado 3.0 标准的 searchUrl 规范：
    1. 简单 GET URL: https://example.com/s?q={{key}}
    2. 带 JSON 配置的高级格式:
       https://example.com/s.php,{
         "method": "POST",
         "body": "keyword={{key}}&t=1",
         "charset": "UTF-8",
         "headers": { ... }
       }
    3. 支持 @js: / <js> 语法提炼与单引号 JSON 配置
    """
    import urllib.parse

    src_label = f"{source_name} (ID:{source_id})" if (source_name or source_id) else "搜索请求"

    spec = extract_legado_search_url_spec(search_spec, base_url)
    if not spec:
        logger.warning("[搜索网络] [%s] searchUrl 为空或无法解析: %s", src_label, search_spec)
        raise ValueError("searchUrl 为空或无法解析")

    url = spec
    options = {}

    if "," in spec:
        idx = spec.find(",")
        raw_url = spec[:idx].strip()
        raw_json = spec[idx + 1:].strip()
        if (raw_json.startswith("{") and raw_json.endswith("}")) or (raw_json.startswith("'{") and raw_json.endswith("}'")):
            options = _parse_options_json(raw_json)
            url = raw_url

    method = str(options.get("method", "GET")).upper()
    charset = str(options.get("charset", "UTF-8")).upper()

    # 编码关键词
    if charset in ("GBK", "GB2312", "GB18030"):
        try:
            esc = urllib.parse.quote(keyword.encode(charset.lower()))
        except Exception:
            esc = urllib.parse.quote(keyword)
    else:
        esc = urllib.parse.quote(keyword)

    def _replace_key(text: str) -> str:
        if not text:
            return ""
        t = (
            text.replace("{{key}}", esc)
            .replace("{{search}}", esc)
            .replace("{search}", esc)
            .replace("{{keyword}}", esc)
            .replace("{{page}}", "1")
            .replace("{{page+1}}", "2")
            .replace("{{page-1}}", "0")
            .replace("{{(page-1)*10}}", "0")
            .replace("{{(page-1)*50}}", "0")
        )
        return re.sub(r"\{\{.*?\}\}", "1", t)

    target_url = _replace_key(url).strip()

    # 如果是相对路径，拼接 base_url
    if base_url and not (target_url.startswith("http://") or target_url.startswith("https://")):
        target_url = urljoin(base_url, target_url)

    # 检验 URL 合法性
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        logger.warning("[搜索网络] [%s] 无效的书源搜索地址: %s", src_label, target_url or search_spec)
        raise ValueError(f"无效的书源搜索地址: {target_url or search_spec}")

    req_headers = {
        "User-Agent": UA,
    }
    if "headers" in options and isinstance(options["headers"], dict):
        req_headers.update(options["headers"])

    raw_body = options.get("body")
    post_data = None

    if method == "POST":
        if raw_body is not None:
            if isinstance(raw_body, dict):
                body_dict = {}
                for k, v in raw_body.items():
                    body_dict[k] = _replace_key(str(v))
                post_data = body_dict
            else:
                post_data = _replace_key(str(raw_body))
                if "Content-Type" not in req_headers:
                    req_headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            post_data = f"keyword={esc}"
            if "Content-Type" not in req_headers:
                req_headers["Content-Type"] = "application/x-www-form-urlencoded"

        body_preview = str(post_data)[:80] if post_data is not None else ""
        logger.info(
            "[搜索网络] [%s] 发起 HTTP POST 请求: %s (编码: %s, 超时: %ds, 载荷: %s)",
            src_label,
            target_url,
            charset,
            timeout,
            body_preview,
        )
    else:
        # GET 请求
        if "?" not in target_url and ("{{key}}" not in search_spec and "{search}" not in search_spec):
            target_url = f"{target_url}?keyword={esc}"
        logger.info(
            "[搜索网络] [%s] 发起 HTTP GET 请求: %s (编码: %s, 超时: %ds)",
            src_label,
            target_url,
            charset,
            timeout,
        )

    search_candidates = [target_url]
    if get_m_to_www():
        conv_www = convert_m_to_www(target_url)
        if conv_www != target_url:
            search_candidates = [conv_www, target_url]
        else:
            conv_m = convert_www_to_m(target_url)
            if conv_m != target_url:
                search_candidates = [target_url, conv_m]

    last_err = None
    for idx, req_url in enumerate(search_candidates):
        is_fallback = idx > 0
        if is_fallback:
            logger.warning("[搜索网络] [%s] 尝试 www. 搜索域名失败，自动回退至移动端搜索 -> %s", src_label, req_url)
        t0 = time.perf_counter()
        try:
            if method == "POST":
                resp = cffi_requests.post(
                    req_url,
                    data=post_data,
                    headers=req_headers,
                    impersonate="chrome120",
                    timeout=timeout,
                    proxy=get_proxy() or None,
                    verify=False,
                )
            else:
                resp = cffi_requests.get(
                    req_url,
                    headers=req_headers,
                    impersonate="chrome120",
                    timeout=timeout,
                    proxy=get_proxy() or None,
                    verify=False,
                )

            resp.raise_for_status()
            content = resp.content or b""
            elapsed_ms = int((time.perf_counter() - t0) * 1000)

            try:
                if charset in ("GBK", "GB2312", "GB18030"):
                    html = content.decode(charset.lower(), errors="replace")
                else:
                    html = resp.text
                    if "charset=gbk" in html.lower() or "charset=gb2312" in html.lower():
                        html = content.decode("gbk", errors="replace")
            except Exception:
                html = resp.text

            logger.info(
                "[搜索网络] [%s] HTTP 响应成功%s: 状态码 %d, 耗时 %dms, 响应大小 %d 字节, 最终URL: %s",
                src_label,
                " (域名回退成功)" if is_fallback else "",
                resp.status_code,
                elapsed_ms,
                len(content),
                str(resp.url or req_url),
            )
            return html, str(resp.url or req_url)

        except Exception as e:
            last_err = e
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            logger.warning(
                "[搜索网络] [%s] HTTP 请求失败%s: %s (耗时 %dms, 目标URL: %s)",
                src_label,
                " (www. 域名首选尝试)" if len(search_candidates) > 1 and idx == 0 else "",
                e,
                elapsed_ms,
                req_url,
            )
            if len(search_candidates) > 1 and idx == 0:
                continue

    if last_err:
        raise last_err
    raise ValueError(f"搜索请求失败: {target_url}")


def normalize_extract_rule(rule: str, default: str) -> str:
    """把 `href` / `src` 补成 `@href`，避免被当成 CSS 选择器。"""
    r = (rule or "").strip()
    if not r:
        return default
    if r in ("href", "src", "text", "html", "ownText", "textNodes") and "@" not in r:
        return f"@{r}" if r in ("href", "src") else r
    return r


def extract_values(el: Tag | None, rule: str, base_url: str = "") -> list[str]:
    """
    通用值提取引擎，支持：
    1. XPath (//a[...] / /select/option/...)
    2. Legado 级联属性选择器 (id.info@tag.p.0@text, class.next@tag.a@href, onclick##...##$1, option@value)
    3. 多值列表展开与 ## 正则替换及 $1 分组反向引用
    """
    if el is None:
        return []
    rule = (rule or "").strip()
    if not rule:
        return []

    # 1. XPath 支持 (// 或 /)
    if rule.startswith("//") or (rule.startswith("/") and not rule.startswith("/@")):
        try:
            import lxml.html
            tree = lxml.html.fromstring(str(el))
            xp_res = tree.xpath(rule)
            out = []
            for item in xp_res:
                if isinstance(item, str):
                    s = item.strip()
                    if s:
                        if base_url and not (s.startswith("http://") or s.startswith("https://")):
                            s = urllib.parse.urljoin(base_url, s)
                        out.append(s)
                elif hasattr(item, "text_content"):
                    s = item.text_content().strip()
                    if s:
                        out.append(s)
            if out:
                return out
        except Exception:
            pass

    # 分离基础规则与 ## 正则替换部分
    parts = rule.split("##")
    base_rule = parts[0].strip()
    replacements = parts[1:]

    # 处理 || fallback
    if "||" in base_rule:
        for branch in base_rule.split("||"):
            res = extract_values(el, branch.strip(), base_url)
            if res:
                return res
        return []

    # 解析 @ 分段链路（例如 id.info@tag.p.0@text 或 class.next@tag.a@href 或 onclick 或 option@value）
    segments = [s.strip() for s in base_rule.split("@") if s.strip()] if "@" in base_rule else ([base_rule] if base_rule else [])

    attr = "text"
    selector_chain = []

    if not segments:
        attr = "text"
    elif len(segments) == 1:
        seg = segments[0]
        seg_lower = seg.lower()
        if el.has_attr(seg):
            attr = seg
        elif seg_lower in ("text", "textn", "textnodes", "owntext", "html", "href", "src", "value", "onclick", "title", "alt", "id", "class", "content", "data-src", "data-url"):
            attr = seg_lower
        else:
            selector_chain = segments
    else:
        attr = segments[-1]
        selector_chain = segments[:-1]

    current_nodes = [el]
    for sel in selector_chain:
        next_nodes = []
        for node in current_nodes:
            next_nodes.extend(safe_select(node, sel))
        current_nodes = next_nodes
        if not current_nodes:
            break

    out = []
    for node in current_nodes:
        if attr in ("text", "textn", "textnodes", "owntext"):
            val = node.get_text(separator=" ", strip=True)
        elif attr == "html":
            val = "".join(str(c) for c in node.contents).strip()
        else:
            v = node.get(attr) or ""
            if isinstance(v, list):
                v = v[0] if v else ""
            val = str(v).strip()
            if attr in ("href", "src", "value", "data-src", "data-url") and base_url and val and not (val.startswith("http://") or val.startswith("https://") or val.startswith("javascript:")):
                val = urllib.parse.urljoin(base_url, val)
            if attr in ("href", "src", "value") and val:
                val = normalize_source_url(val)

        # 执行 ## 正则替换并支持 $1, $2 分组反向引用
        for i in range(0, len(replacements), 2):
            pattern = replacements[i].strip()
            if not pattern:
                continue
            repl = replacements[i + 1] if i + 1 < len(replacements) else ""
            # 将 $1, $2 转换为 \g<1>, \g<2>
            def _fix_dollar(r_str: str) -> str:
                out_r = ""
                k = 0
                while k < len(r_str):
                    if r_str[k] == "$" and k + 1 < len(r_str) and r_str[k + 1].isdigit():
                        m = k + 1
                        while m < len(r_str) and r_str[m].isdigit():
                            m += 1
                        num = r_str[k + 1 : m]
                        out_r += "\\g<" + num + ">"
                        k = m
                    else:
                        out_r += r_str[k]
                        k += 1
                return out_r

            repl = _fix_dollar(repl)
            try:
                val = re.sub(pattern, repl, val)
            except Exception:
                pass

        val = val.strip()
        if val:
            if base_url and not (val.startswith("http://") or val.startswith("https://") or val.startswith("javascript:")):
                if val.startswith("/") or val.startswith("./") or val.startswith("../") or ".html" in val or ".php" in val:
                    val = urllib.parse.urljoin(base_url, val)
            out.append(val)
    return out


def extract_value(el: Tag | None, rule: str, base_url: str = "") -> str:
    """提取首个匹配值。"""
    vals = extract_values(el, rule, base_url)
    return vals[0] if vals else ""


def apply_replace_regex(
    content: str,
    rule_str: str,
    book_name: str = "",
    chapter_title: str = "",
) -> str:
    """执行 Legado 3.0 正文净化规则（replaceRegex）。"""
    if not content or not rule_str:
        return content

    rule = rule_str.strip()
    if book_name:
        rule = rule.replace("{{book.name}}", re.escape(book_name)).replace("{{name}}", re.escape(book_name))
    if chapter_title:
        rule = rule.replace("{{book.durChapterTitle}}", re.escape(chapter_title)).replace("{{title}}", re.escape(chapter_title))

    # 提取 <js>...</js> 块中的规则
    js_blocks = re.findall(r"<js>(.*?)</js>", rule, re.DOTALL)
    if js_blocks:
        for b in js_blocks:
            content = apply_replace_regex(content, b, book_name, chapter_title)
        rule = re.sub(r"<js>.*?</js>", "", rule, flags=re.DOTALL).strip()

    # 处理 JS replace 表达式
    if rule.startswith("@js:") or "result.replace" in rule or "content.replace" in rule:
        js_replaces = re.findall(r"\.replace\(/([^/]+)/[a-z]*\s*,\s*['\"]([^'\"]*)['\"]\)", rule)
        for pat, rep in js_replaces:
            try:
                content = re.sub(pat, rep, content)
            except Exception:
                pass
        return content.strip()

    lines = [l.strip() for l in rule.split("\n") if l.strip()]
    for line in lines:
        if line.startswith("##"):
            parts = line.split("##")[1:]
            for i in range(0, len(parts), 2):
                pat = parts[i].strip()
                rep = parts[i + 1] if i + 1 < len(parts) else ""
                if pat:
                    try:
                        content = re.sub(pat, rep, content, flags=re.MULTILINE)
                    except Exception:
                        pass
        elif "##" in line:
            parts = line.split("##")
            for i in range(0, len(parts), 2):
                pat = parts[i].strip()
                rep = parts[i + 1] if i + 1 < len(parts) else ""
                if pat:
                    try:
                        content = re.sub(pat, rep, content, flags=re.MULTILINE)
                    except Exception:
                        pass
        elif line:
            try:
                content = re.sub(line, "", content, flags=re.MULTILINE)
            except Exception:
                pass

    return content.strip()


def crawl_search(
    html: str,
    rule: SearchRule | None,
    base_url: str,
    source_name: str = "",
    source_id: int | str = "",
) -> list[dict]:
    src_label = f"{source_name} (ID:{source_id})" if (source_name or source_id) else "搜索解析"
    if rule is None or not rule.selector:
        logger.warning("[搜索解析] [%s] 缺少有效的搜索列表选择器 (rule.selector 为空)", src_label)
        return []

    t0 = time.perf_counter()
    logger.info(
        "[搜索解析] [%s] 开始解析搜索结果 (列表选择器: 「%s」, 书名规则: 「%s」, 作者规则: 「%s」, 链接规则: 「%s」)",
        src_label,
        rule.selector,
        rule.name or "text",
        rule.author or "无",
        rule.book_url or "a@href",
    )

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    book_url_rule = normalize_extract_rule(rule.book_url, "a@href")
    root = soup if isinstance(soup, Tag) else soup

    elements = safe_select(root, rule.selector)
    if not elements:
        logger.warning(
            "[搜索解析] [%s] 选择器「%s」未匹配到任何书籍节点 (HTML大小: %d 字符)，请检查书源规则或网页结构",
            src_label,
            rule.selector,
            len(html),
        )
        return []

    logger.info("[搜索解析] [%s] 选择器「%s」共匹配到 %d 个候选条目", src_label, rule.selector, len(elements))

    extract_fails = 0
    for s in elements:
        try:
            name = extract_value(s, _or_default(rule.name, "text"), base_url).strip()
            author = extract_value(s, rule.author, base_url).strip()
            cover = extract_value(s, rule.cover, base_url).strip()
            intro = extract_value(s, rule.intro, base_url).strip()
            burl = extract_value(s, book_url_rule, base_url).strip()
            if not name and not burl:
                extract_fails += 1
                continue
            items.append(
                {
                    "name": name,
                    "author": author,
                    "cover": cover,
                    "intro": intro,
                    "bookUrl": burl,
                }
            )
        except Exception:
            extract_fails += 1
            continue

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    samples = [f"《{b['name']}》({b['author'] or '未知作者'})" for b in items[:3]]
    sample_str = ", ".join(samples) + (" 等" if len(items) > 3 else "")
    logger.info(
        "[搜索解析] [%s] 搜索结果提取完成: 共成功解析出 %d 本书籍 (耗时 %dms%s)%s",
        src_label,
        len(items),
        elapsed_ms,
        f", 忽略无效条目 {extract_fails} 个" if extract_fails else "",
        f": {sample_str}" if items else "",
    )
    return items


def crawl_detail(
    html: str,
    rule: DetailRule | None,
    base_url: str,
    source_name: str = "",
    source_id: int | str = "",
    book_name: str = "",
) -> DetailRule:
    out = DetailRule()
    if rule is None:
        return out
    src_label = f"{source_name} (ID:{source_id})" if (source_name or source_id) else "详情解析"
    book_label = f"《{book_name}》" if book_name else "书籍"

    t0 = time.perf_counter()
    logger.info(
        "[书籍详情] [%s] 开始解析%s详情 (简介规则: 「%s」, 作者规则: 「%s」, 封面规则: 「%s」)",
        src_label,
        book_label,
        rule.intro or "无",
        rule.author or "无",
        rule.cover or "无",
    )
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

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    intro_preview = (out.intro[:40] + "...") if len(out.intro) > 40 else out.intro
    logger.info(
        "[书籍详情] [%s] %s详情解析完成: 作者:「%s」, 封面:「%s」, 简介:「%s」 (耗时 %dms)",
        src_label,
        book_label,
        out.author or "未提取",
        out.cover or "未提取",
        intro_preview or "未提取",
        elapsed_ms,
    )
    return out


_INVALID_CHAPTER_PATTERNS = re.compile(
    r"^(查看全部章节|查看完整目录|查看目录|全部章节|全部目录|完整目录|所有章节|最新章节|作品相关|正文卷|展开全部|展开|收起|下一页|上一页|返回书页|加入书架|加书签|投推荐票|投月票|打赏|倒序|正序|目录)[>\s\-_~]*$",
    re.IGNORECASE,
)


def _is_invalid_chapter_title(title: str) -> bool:
    t = (title or "").strip()
    if not t:
        return True
    return bool(_INVALID_CHAPTER_PATTERNS.match(t))


def _find_catalog_link_in_html(html: str, base_url: str) -> str:
    """在详情页 HTML 中自动寻找通往全量目录列表的链接（如“查看全部章节 >>”）。"""
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return ""
    for a in soup.find_all("a"):
        txt = a.get_text(strip=True)
        href = a.get("href", "")
        if href and _is_invalid_chapter_title(txt) and any(k in txt for k in ["查看全部章节", "查看目录", "全部章节", "完整目录", "全部目录", "所有章节"]):
            full_url = urllib.parse.urljoin(base_url, href)
            if full_url != base_url:
                return full_url
    return ""


def crawl_toc(
    html: str,
    rule: TocRule | None,
    base_url: str,
    source_name: str = "",
    source_id: int | str = "",
    book_name: str = "",
) -> list[dict]:
    src_label = f"{source_name} (ID:{source_id})" if (source_name or source_id) else "目录解析"
    book_label = f"《{book_name}》" if book_name else "书籍"

    if rule is None or not rule.selector:
        logger.warning("[目录解析] [%s] %s缺少目录列表选择器 (rule.toc.selector 为空)", src_label, book_label)
        return []

    t0 = time.perf_counter()
    logger.info(
        "[目录解析] [%s] 开始解析%s目录 (列表选择器: 「%s」, 标题规则: 「%s」, 章节链接: 「%s」)",
        src_label,
        book_label,
        rule.selector,
        rule.title or "text",
        rule.chapter_url or "@href",
    )

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    seen = set()
    root = soup if isinstance(soup, Tag) else soup

    elements = safe_select(root, rule.selector)
    if not elements:
        logger.warning(
            "[目录解析] [%s] %s目录选择器「%s」未匹配到任何章节节点 (页面大小: %d 字符)，请检查书源目录规则或反爬拦截",
            src_label,
            book_label,
            rule.selector,
            len(html),
        )
        return []

    logger.info("[目录解析] [%s] %s目录选择器「%s」共匹配到 %d 个原始节点", src_label, book_label, rule.selector, len(elements))

    duplicate_count = 0
    empty_count = 0
    title_rule = _or_default(rule.title, "text")
    chapter_url_rule = normalize_extract_rule(rule.chapter_url, "@href")

    for s in elements:
        title = extract_value(s, title_rule, base_url).strip()
        url = extract_value(s, chapter_url_rule, base_url).strip()
        if not title and not url:
            empty_count += 1
            continue
        if _is_invalid_chapter_title(title):
            empty_count += 1
            continue
        key = url if url else title
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        out.append({"title": title or "未知章节", "chapterUrl": url})

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    first_title = out[0]["title"] if out else "无"
    last_title = out[-1]["title"] if out else "无"

    logger.info(
        "[目录解析] [%s] %s目录解析完成: 共提取 %d 个有效章节 (去重 %d 个, 过滤无效 %d 个, 耗时 %dms) [首章:「%s」, 末章:「%s」]",
        src_label,
        book_label,
        len(out),
        duplicate_count,
        empty_count,
        elapsed_ms,
        first_title,
        last_title,
    )
    return out


def is_same_chapter_subpage(cur_url: str, next_url: str) -> bool:
    """
    判断 next_url 是否为当前章节的后续子分页（而非跳转到下一章）。
    例如：
      /book/1/1001.html -> /book/1/1001_2.html  (True，同章第2页)
      /book/1/1001_1.html -> /book/1/1001_2.html(True，同章第2页)
      /book/1/1001.html -> /book/1/1001-2.html  (True)
      /book/1/1001.html?page=1 -> /book/1/1001.html?page=2 (True)
      /book/1/1001.html -> /book/1/1002.html   (False，这是下一章)
    """
    if not cur_url or not next_url or cur_url == next_url:
        return False
    try:
        p_cur = urllib.parse.urlparse(cur_url)
        p_next = urllib.parse.urlparse(next_url)
    except Exception:
        return False

    if p_cur.netloc != p_next.netloc:
        return False

    # 1. 相同路径，仅查询参数分页（如 ?page=2 或 &p=2）
    if p_cur.path == p_next.path and p_next.query != p_cur.query:
        return True

    cur_path = p_cur.path.rstrip("/")
    next_path = p_next.path.rstrip("/")

    cur_base, cur_ext = cur_path.rsplit(".", 1) if "." in cur_path.split("/")[-1] else (cur_path, "")
    next_base, next_ext = next_path.rsplit(".", 1) if "." in next_path.split("/")[-1] else (next_path, "")

    # 2. 带有 _2, _3, -2, -3 后缀的子分页
    cur_stem = re.sub(r"[_\-](\d+)$", "", cur_base)
    next_stem_m = re.search(r"^(.*?)[_\-](\d+)$", next_base)
    if next_stem_m:
        next_stem = next_stem_m.group(1)
        if next_stem == cur_stem or next_stem == cur_base:
            return True

    # 3. 路径层级子分页 /book/1/1001/ -> /book/1/1001/2
    if next_path.startswith(cur_path + "/") and re.match(r"^\d+$", next_path[len(cur_path) + 1:]):
        return True

    return False


def extract_next_content_url(
    soup: BeautifulSoup,
    cur_url: str,
    rule_str: str = "",
    base_url: str = "",
) -> str:
    """提取章节正文的下一页子分页链接。"""
    raw_rule = (rule_str or "").strip()

    # 1. 优先使用书源规则提取
    if raw_rule:
        js_code = ""
        selector_part = raw_rule
        if "<js>" in raw_rule:
            m_js = re.search(r"<js>(.*?)</js>", raw_rule, re.DOTALL)
            if m_js:
                js_code = m_js.group(1).strip()
            selector_part = re.sub(r"<js>.*?</js>", "", raw_rule, flags=re.DOTALL).strip()
        elif "@js:" in raw_rule:
            parts = raw_rule.split("@js:", 1)
            selector_part = parts[0].strip()
            js_code = parts[1].strip()

        candidates = extract_values(soup, selector_part, cur_url)
        for cand in candidates:
            cand_url = cand
            if js_code:
                m_filter = re.search(r"/([^/]+)/\.test\(result\)\s*\?\s*result\s*:\s*['\"]([^'\"]*)['\"]", js_code)
                if m_filter:
                    pat, fallback = m_filter.group(1), m_filter.group(2)
                    cand_url = cand_url if re.search(pat, cand_url) else fallback

            if cand_url:
                full_next = abs_url(cur_url, cand_url)
                if full_next and full_next != cur_url:
                    if js_code or is_same_chapter_subpage(cur_url, full_next):
                        return full_next

    # 2. 启发式自动寻找同章下一页链接
    for a in soup.find_all("a"):
        txt = a.get_text(strip=True)
        href = a.get("href", "")
        if not href or not txt:
            continue
        if any(bad in txt for bad in ["下一章", "下一篇", "下章", "上一章", "上一页", "上页", "返回目录", "目录", "加入书签"]):
            continue
        if txt in ["下一页", "下一页>", "下一页 >", "下一页»", "下页", "后页", "下一页(2/3)", "第2页", "第3页", "第4页"] or (txt.startswith("下一页") and "章" not in txt):
            full_next = abs_url(cur_url, href)
            if full_next and is_same_chapter_subpage(cur_url, full_next):
                return full_next

    return ""


def fetch_all_toc(
    initial_url: str,
    rule: TocRule,
    source_name: str = "",
    source_id: int | str = "",
    book_name: str = "",
    initial_html: str | None = None,
    max_pages: int = 80,
) -> list[dict]:
    """抓取目录，支持分页跟进（下一页 / 下拉选单 option@value / nextTocUrl）并汇聚完整章节列表。"""
    pending_urls: list[str] = [initial_url]
    all_chapters: list[dict] = []
    seen_keys: set[str] = set()
    visited_pages: set[str] = set()
    page = 0
    cur_html = initial_html

    while pending_urls and page < max_pages:
        cur_url = pending_urls.pop(0)
        if cur_url in visited_pages:
            continue
        visited_pages.add(cur_url)
        page += 1

        if cur_html is None:
            try:
                cur_html = fetch_url(cur_url, context=f"目录第{page}页:{book_name}")
            except Exception as e:
                logger.warning("[目录分页] [%s] 《%s》抓取目录第 %d 页失败 (%s): %s", source_name, book_name, page, cur_url, e)
                cur_html = None
                continue

        page_chapters = crawl_toc(
            cur_html,
            rule,
            cur_url,
            source_name=source_name,
            source_id=source_id,
            book_name=book_name,
        )

        for c in page_chapters:
            key = c.get("chapterUrl") or c.get("title") or ""
            if key and key not in seen_keys:
                seen_keys.add(key)
                all_chapters.append(c)

        # 发现后续目录页链接
        try:
            soup = BeautifulSoup(cur_html, "html.parser")
            found_next_urls = []

            # 1. 优先根据 rule.next_toc_url 提取
            if rule.next_toc_url:
                cands = extract_values(soup, rule.next_toc_url, cur_url)
                for cand in cands:
                    full_u = abs_url(cur_url, cand)
                    if full_u and full_u not in visited_pages and full_u not in pending_urls:
                        found_next_urls.append(full_u)

            # 2. 启发式：若未找到，检查 <select> 目录下拉分页与 <a ...> 下一页链接
            if not found_next_urls:
                for sel in soup.find_all("select"):
                    opts = sel.find_all("option")
                    if len(opts) > 1:
                        for opt in opts:
                            v = opt.get("value", "").strip()
                            if v:
                                full_u = abs_url(cur_url, v)
                                if full_u and full_u not in visited_pages and full_u not in pending_urls:
                                    found_next_urls.append(full_u)

                for a in soup.find_all("a"):
                    txt = a.get_text(strip=True)
                    href = a.get("href", "")
                    if href and (txt in ["下一页", "下一章列表", "下页", "下一部", "后页", "下一页 >", "下一页»"] or (txt.startswith("下一") and "章" not in txt)):
                        full_next = abs_url(cur_url, href)
                        if full_next and full_next not in visited_pages and full_next not in pending_urls:
                            found_next_urls.append(full_next)
                            break

            for u in found_next_urls:
                if u not in visited_pages and u not in pending_urls:
                    pending_urls.append(u)
        except Exception:
            pass

        cur_html = None

    return all_chapters


def preprocess_js_rendered_content(soup: BeautifulSoup) -> None:
    """
    针对小说站点（如 69小说吧、yaolu、uxx、biquge 变体等）通过前端 JavaScript 动态将 Base64 / 混淆正文注入 DOM 容器的情况，
    自动解析并将解码后的 HTML 注入到相应的 DOM 容器（如 #rtext, #content, .content 等）中。
    """
    import base64

    for script in soup.find_all("script"):
        script_text = script.get_text()
        if not script_text or len(script_text) < 30:
            continue

        target_ids = re.findall(r"document\.getElementById\(['\"]([\w\-]+)['\"]\)\.innerHTML\s*=", script_text)
        target_ids += re.findall(r"\$\(['\"]#([\w\-]+)['\"]\)\.html\(", script_text)

        b64_matches = re.findall(
            r"(?:encoded|content|html_data|chapter_content|txt_content|b64|raw_content|article_content)\s*=\s*[\"']([A-Za-z0-9+/=]{40,})[\"']",
            script_text,
            re.IGNORECASE,
        )
        if not b64_matches:
            b64_candidates = re.findall(r"[\"']([A-Za-z0-9+/=]{100,})[\"']", script_text)
            for cand in b64_candidates:
                if cand.startswith("PHA+") or cand.startswith("PD") or cand.startswith("PG") or cand.startswith("Cg"):
                    b64_matches.append(cand)

        for b64_str in b64_matches:
            try:
                decoded_bytes = base64.b64decode(b64_str)
                decoded_text = ""
                for enc in ("utf-8", "gbk", "gb18030"):
                    try:
                        decoded_text = decoded_bytes.decode(enc)
                        break
                    except Exception:
                        pass

                if decoded_text and ("<p>" in decoded_text or "class=" in decoded_text or len(decoded_text) > 60):
                    injected = False
                    for tid in target_ids:
                        target_elem = soup.find(id=tid)
                        if target_elem is not None:
                            sub_soup = BeautifulSoup(decoded_text, "html.parser")
                            target_elem.clear()
                            target_elem.append(sub_soup)
                            injected = True

                    if not injected:
                        for def_id in ("rtext", "content", "chaptercontent", "htmlContent", "nr", "txt", "text", "article"):
                            target_elem = soup.find(id=def_id)
                            if target_elem is not None and not target_elem.get_text(strip=True):
                                sub_soup = BeautifulSoup(decoded_text, "html.parser")
                                target_elem.clear()
                                target_elem.append(sub_soup)
                                injected = True
                                break
            except Exception:
                pass


def crawl_content_single_page(
    html: str,
    rule: ContentRule | None,
    source_name: str = "",
    source_id: int | str = "",
    book_name: str = "",
    chapter_title: str = "",
) -> list[str]:
    """提取单页正文段落列表。"""
    src_label = f"{source_name} (ID:{source_id})" if (source_name or source_id) else "正文解析"
    title_label = f"《{book_name}》-「{chapter_title}」" if (book_name or chapter_title) else "章节正文"

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    # 预处理：解析并注入 JS 动态 Base64 / 混淆编码正文
    preprocess_js_rendered_content(soup)

    if rule is None or not rule.selector:
        text = soup.get_text(separator="\n", strip=True)
        return [p.strip() for p in text.split("\n") if p.strip()]

    root = soup if isinstance(soup, Tag) else soup
    elems = safe_select(root, rule.selector)

    paragraphs = []
    text_rule = _or_default(rule.text, "text")
    if elems:
        for el in elems:
            p_text = extract_value(el, text_rule, "")
            if p_text:
                paragraphs.append(p_text)

    # 保底机制 1：如果规则指定了 p 标签选择器（如 #rtext p），但容器内直接包含纯文本或换行，尝试直接从容器本身提取
    if not paragraphs and rule.selector and " p" in rule.selector:
        parent_sel = rule.selector.split(" p", 1)[0].strip()
        if parent_sel:
            parent_elems = safe_select(root, parent_sel)
            if parent_elems:
                raw_text = parent_elems[0].get_text(separator="\n", strip=True)
                candidate_paras = [p.strip() for p in raw_text.split("\n") if p.strip()]
                if candidate_paras:
                    paragraphs = candidate_paras
                    logger.info("[正文解析] [%s] %s通过父容器 %s 备选提取到 %d 个段落", src_label, title_label, parent_sel, len(paragraphs))

    # 保底机制 2：如果提取结果依然为空，尝试常见正文容器保底选择器
    if not paragraphs:
        for fallback_sel in ("#rtext", "#content", "#chaptercontent", "#htmlContent", ".read-content", ".content", "#nr", "#txt", "article"):
            fb_elems = safe_select(root, fallback_sel)
            if fb_elems:
                fb_text = fb_elems[0].get_text(separator="\n", strip=True)
                fb_paras = [p.strip() for p in fb_text.split("\n") if p.strip()]
                if len(fb_paras) >= 3 or (fb_paras and len("".join(fb_paras)) > 100):
                    paragraphs = fb_paras
                    logger.info("[正文解析] [%s] %s主规则未命中，通过备选容器 %s 提取到 %d 个段落", src_label, title_label, fallback_sel, len(paragraphs))
                    break

    return paragraphs


def crawl_content(
    html: str,
    rule: ContentRule | None,
    source_name: str = "",
    source_id: int | str = "",
    book_name: str = "",
    chapter_title: str = "",
) -> str:
    paragraphs = crawl_content_single_page(
        html,
        rule,
        source_name=source_name,
        source_id=source_id,
        book_name=book_name,
        chapter_title=chapter_title,
    )
    content = "\n".join(paragraphs)
    if rule and rule.replace_regex:
        content = apply_replace_regex(content, rule.replace_regex, book_name=book_name, chapter_title=chapter_title)
    return content


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


def _resolve_toc_url(book: dict, rule: SourceRule, book_name: str = "") -> tuple[str, str | None]:
    """
    解析真实目录 URL。
    返回 (real_toc_url, detail_html_if_fetched)
    只有当 real_toc_url == book_url 时，detail_html 才可以复用为目录 HTML。
    """
    book_url = book.get("source_url") or ""
    raw = (rule.toc.url if rule.toc else "") or ""
    if raw:
        raw = raw.replace("{{bookUrl}}", book_url).replace("{bookUrl}", book_url)
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw, None
        if raw.startswith("/") and "@" not in raw and not any(c in raw for c in ["*", "[", ">", ":", "."]):
            return urllib.parse.urljoin(book_url, raw), None

        # raw 是选择器规则，先抓取详情页 HTML
        try:
            detail_html = fetch_url(book_url, context=f"详情页TOC解析:{book_name}")
            soup = BeautifulSoup(detail_html, "html.parser")
            extracted = extract_value(soup, raw, book_url)
            if extracted and extracted != book_url:
                return urllib.parse.urljoin(book_url, extracted), None
            # 自动发现“查看全部章节”
            auto_toc = _find_catalog_link_in_html(detail_html, book_url)
            if auto_toc and auto_toc != book_url:
                return auto_toc, None
            return book_url, detail_html
        except Exception:
            return book_url, None

    # raw 为空，在详情页寻找是否存在“查看全部章节”
    try:
        detail_html = fetch_url(book_url, context=f"详情页:{book_name}")
        auto_toc = _find_catalog_link_in_html(detail_html, book_url)
        if auto_toc and auto_toc != book_url:
            return auto_toc, None
        return book_url, detail_html
    except Exception:
        return book_url, None


def _toc_url(book: dict, rule: SourceRule) -> str:
    url, _ = _resolve_toc_url(book, rule, book.get("name") or "")
    return url


def refresh_web_chapters(book: dict) -> None:
    book_id = book.get("id") or 0
    book_name = book.get("name") or "未知书籍"
    src_id = int(book.get("source_id") or 0)
    src = source_by_id(src_id)
    if not src:
        logger.error("[目录抓取] 书籍《%s》(ID:%s) 绑定的书源 (ID:%s) 不存在", book_name, book_id, src_id)
        raise ValueError("无书源")

    rule = _rule_for_source(src)
    if rule.toc is None or not rule.toc.selector:
        logger.warning("[目录抓取] [%s (ID:%s)] 书籍《%s》的书源无有效目录规则", src["name"], src["id"], book_name)
        raise ValueError("无目录规则")

    toc_url, initial_html = _resolve_toc_url(book, rule, book_name=book_name)
    if not toc_url:
        logger.warning("[目录抓取] [%s (ID:%s)] 书籍《%s》缺少目录请求地址", src["name"], src["id"], book_name)
        raise ValueError("缺少书籍地址")

    logger.info("[目录抓取] [%s (ID:%s)] 开始为《%s》(ID:%s) 抓取目录 -> %s", src["name"], src["id"], book_name, book_id, toc_url)
    t0 = time.perf_counter()
    try:
        toc = fetch_all_toc(
            toc_url,
            rule.toc,
            source_name=src["name"],
            source_id=src["id"],
            book_name=book_name,
            initial_html=initial_html,
        )
    except Exception as e:
        logger.error("[目录抓取] [%s (ID:%s)] 《%s》(ID:%s) 目录抓取失败: %s (URL: %s)", src["name"], src["id"], book_name, book_id, e, toc_url)
        raise

    if not toc:
        logger.warning("[目录抓取] [%s (ID:%s)] 《%s》(ID:%s) 未解析出任何有效章节", src["name"], src["id"], book_name, book_id)
        raise ValueError(f"书源【{src['name']}】未解析出任何有效章节，请检查书源规则或网络")

    db_t0 = time.perf_counter()
    conn = require_db()
    conn.execute("DELETE FROM chapter WHERE book_id=?", (book_id,))
    conn.executemany(
        "INSERT INTO chapter (book_id, title, idx, content_url) VALUES (?, ?, ?, ?)",
        [(book_id, c["title"], i, c["chapterUrl"]) for i, c in enumerate(toc)],
    )
    conn.commit()
    db_elapsed_ms = int((time.perf_counter() - db_t0) * 1000)
    total_elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "[目录入库] 《%s》(ID:%s) 成功写入 %d 个章节至数据库 (写入耗时 %dms, 整体耗时 %dms)",
        book_name,
        book_id,
        len(toc),
        db_elapsed_ms,
        total_elapsed_ms,
    )


def fetch_web_chapter(book: dict, chapter_url: str, chapter_title: str = "") -> str:
    """
    抓取网络章节正文，支持同章多页分页自动合并与净化（nextContentUrl 与启发式子分页）。
    """
    book_id = book.get("id") or 0
    book_name = book.get("name") or "未知书籍"
    src_id = int(book.get("source_id") or 0)
    src = source_by_id(src_id)
    if not src:
        logger.error("[正文抓取] 书籍《%s》(ID:%s) 绑定的书源 (ID:%s) 不存在", book_name, book_id, src_id)
        raise ValueError("无书源")

    rule = _rule_for_source(src)
    if rule.content is None:
        logger.warning("[正文抓取] [%s (ID:%s)] 书籍《%s》无有效正文规则", src["name"], src["id"], book_name)
        raise ValueError("无内容规则")

    target = chapter_url or book.get("source_url") or ""
    if not target:
        logger.warning("[正文抓取] [%s (ID:%s)] 《%s》缺失章节地址", src["name"], src["id"], book_name)
        raise ValueError("缺少章节地址")

    t_label = f"「{chapter_title}」" if chapter_title else ""
    logger.info("[正文抓取] [%s (ID:%s)] 开始抓取《%s》%s正文 -> %s", src["name"], src["id"], book_name, t_label, target)

    cur_url = target
    visited_urls: set[str] = set()
    all_paragraphs: list[str] = []
    page = 0
    max_chapter_pages = 25
    t0 = time.perf_counter()

    while cur_url and cur_url not in visited_urls and page < max_chapter_pages:
        visited_urls.add(cur_url)
        page += 1
        ctx = f"正文页{f'(第{page}页)' if page > 1 else ''}:{book_name}{t_label}"
        try:
            html = fetch_url(cur_url, context=ctx)
        except Exception as e:
            logger.error("[正文抓取] [%s (ID:%s)] 《%s》%s抓取第 %d 页失败: %s (URL: %s)", src["name"], src["id"], book_name, t_label, page, e, cur_url)
            if page == 1:
                raise
            break

        # 解析本页正文段落
        page_paras = crawl_content_single_page(
            html,
            rule.content,
            source_name=src["name"],
            source_id=src["id"],
            book_name=book_name,
            chapter_title=chapter_title,
        )

        # 若多页分页在后续页顶部重复了章节名（如“第一章 ... (第2页)”），剔除重复标题段落
        if page > 1 and page_paras and chapter_title:
            first_p = page_paras[0].strip()
            clean_ct = re.sub(r"\s+", "", chapter_title)
            clean_fp = re.sub(r"\s+|（.*?）|\(.*?\)|第\d+页", "", first_p)
            if clean_fp == clean_ct or (len(clean_ct) >= 2 and clean_ct in clean_fp):
                page_paras = page_paras[1:]

        all_paragraphs.extend(page_paras)

        # 检查本章是否存在下一页子分页
        try:
            soup = BeautifulSoup(html, "html.parser")
            next_url = extract_next_content_url(soup, cur_url, rule.content.next_content_url, base_url=target)
        except Exception:
            next_url = ""

        if next_url and next_url not in visited_urls:
            logger.info("[正文分页] [%s] 《%s》%s发现同章后续分页第 %d 页 -> %s", src["name"], book_name, t_label, page + 1, next_url)
            cur_url = next_url
        else:
            cur_url = ""

    full_content = "\n".join(all_paragraphs)
    if rule.content.replace_regex:
        full_content = apply_replace_regex(full_content, rule.content.replace_regex, book_name=book_name, chapter_title=chapter_title)

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    logger.info(
        "[正文完成] [%s (ID:%s)] 《%s》%s正文抓取完成: 共合并 %d 个子分页, %d 个段落, 总计 %d 字符 (耗时 %dms)",
        src["name"],
        src["id"],
        book_name,
        t_label,
        page,
        len(all_paragraphs),
        len(full_content),
        elapsed_ms,
    )
    return full_content


def crawl_book_detail(book: dict) -> DetailRule:
    book_id = book.get("id") or 0
    book_name = book.get("name") or "未知书籍"
    src_id = int(book.get("source_id") or 0)
    src = source_by_id(src_id)
    if not src:
        logger.error("[书籍详情] 书籍《%s》(ID:%s) 绑定的书源 (ID:%s) 不存在", book_name, book_id, src_id)
        raise ValueError("无书源")
    rule = _rule_for_source(src)
    if rule.detail is None:
        logger.warning("[书籍详情] [%s (ID:%s)] 书籍《%s》无详情规则", src["name"], src["id"], book_name)
        raise ValueError("无详情规则")
    target_url = book.get("source_url") or ""
    logger.info("[书籍详情] [%s (ID:%s)] 开始抓取《%s》(ID:%s) 详情页 -> %s", src["name"], src["id"], book_name, book_id, target_url)
    html = fetch_url(target_url, context=f"详情页:{book_name}")
    return crawl_detail(
        html,
        rule.detail,
        target_url,
        source_name=src["name"],
        source_id=src["id"],
        book_name=book_name,
    )


# ─── 探索 / 发现模块 (Explore Rules) ──────────────────────────

def parse_explore_items(explore_url_str: str) -> list[dict]:
    """解析 Legado 书源中的 exploreUrl 规则定义。"""
    if not explore_url_str:
        return []
    s = explore_url_str.strip()

    # 1. 尝试 JSON 格式解析（支持带注释、单引号、尾随逗号）
    cleaned = re.sub(r"//.*", "", s)
    cleaned = re.sub(r"/\*.*?\*/", "", cleaned, flags=re.DOTALL).strip()

    if cleaned.startswith("[") or cleaned.startswith("{"):
        # 先直接尝试原生 json.loads
        try:
            data = json.loads(cleaned)
            if isinstance(data, list):
                out = []
                for item in data:
                    if isinstance(item, dict):
                        t = str(item.get("title") or item.get("name") or "").strip()
                        u = str(item.get("url") or "").strip()
                        if t and not (t.startswith("@js:") or t in ("[", "]", "{", "}")):
                            out.append({"title": t, "url": u, "style": item.get("style") or {}})
                if out:
                    return out
            elif isinstance(data, dict):
                t = str(data.get("title") or data.get("name") or "").strip()
                u = str(data.get("url") or "").strip()
                if t and not (t.startswith("@js:") or t in ("[", "]", "{", "}")):
                    return [{"title": t, "url": u, "style": data.get("style") or {}}]
        except Exception:
            # 尝试宽松 JSON 修复：尾随逗号、未加双引号的 key
            fix_json = re.sub(r",\s*([\]}])", r"\1", cleaned)
            fix_json = re.sub(r'(?<!")(\b[a-zA-Z_]\w*\b)\s*:', r'"\1":', fix_json)
            try:
                data = json.loads(fix_json)
                if isinstance(data, list):
                    out = []
                    for item in data:
                        if isinstance(item, dict):
                            t = str(item.get("title") or item.get("name") or "").strip()
                            u = str(item.get("url") or "").strip()
                            if t and not (t.startswith("@js:") or t in ("[", "]", "{", "}")):
                                out.append({"title": t, "url": u, "style": item.get("style") or {}})
                    if out:
                        return out
            except Exception:
                pass

    # 2. 如果包含 title 和 url 结构，正则提取对象字典
    if ("title" in s or "title:" in s) and ("url" in s or "url:" in s):
        blocks = re.findall(r"\{[^{}]*\}", s)
        out = []
        for b in blocks:
            m_t = re.search(r'["\']?title["\']?\s*:\s*["\']([^"\']+)["\']', b)
            m_u = re.search(r'["\']?url["\']?\s*:\s*["\']([^"\']*)["\']', b)
            if m_t:
                t = m_t.group(1).strip()
                u = m_u.group(1).strip() if m_u else ""
                if t and not (t.startswith("@js:") or t in ("[", "]", "{", "}", ");", "})")):
                    out.append({"title": t, "url": u, "style": {}})
        if out:
            return out

    # 3. 按行与分隔符解析：支持 Title::url, Title&&Title2::url2, Title\turl, Title\nurl
    lines = [l.strip() for l in s.split("\n") if l.strip()]
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("//") or line.startswith("/*") or line.startswith("*") or line in ("[", "]", "{", "}", ");", "})", ";"):
            i += 1
            continue

        # 包含 && 分割的多个项
        if "&&" in line and "::" in line:
            sub_items = line.split("&&")
            for sub in sub_items:
                if "::" in sub:
                    parts = sub.split("::", 1)
                    t, u = parts[0].strip(), parts[1].strip()
                    if t and not t.startswith("@js:"):
                        out.append({"title": t, "url": u, "style": {}})
            i += 1
            continue

        if "::" in line:
            parts = line.split("::", 1)
            t, u = parts[0].strip(), parts[1].strip()
            if t and not t.startswith("@js:"):
                out.append({"title": t, "url": u, "style": {}})
            i += 1
        elif "\t" in line:
            parts = line.split("\t", 1)
            t, u = parts[0].strip(), parts[1].strip()
            if t and not t.startswith("@js:"):
                out.append({"title": t, "url": u, "style": {}})
            i += 1
        else:
            # 可能是标题占一行，url 在下一行
            if i + 1 < len(lines) and ("/" in lines[i + 1] or "http" in lines[i + 1] or "{{" in lines[i + 1]):
                t = line
                u = lines[i + 1]
                if t and not t.startswith("@js:"):
                    out.append({"title": t, "url": u, "style": {}})
                i += 2
            else:
                # 分组/分类标题（url 为空）
                if line and not (line.startswith("@js:") or line.startswith("sort=") or line.startswith("push=")):
                    out.append({"title": line, "url": "", "style": {}})
                i += 1

    return out


def resolve_explore_url(raw_url: str, page: int = 1, base_url: str = "") -> str:
    """处理 Legado 探索 URL 中的分页宏与尖括号语法。"""
    url = (raw_url or "").strip()
    if not url:
        return ""

    # 处理 <prefix,suffix> 语法（例如 /xuanhuan/<,{{page}}.html> 在第1页为 /xuanhuan/，在第2页为 /xuanhuan/2.html）
    def _replace_angle_brackets(match):
        p1 = match.group(1)
        p2 = match.group(2)
        return p1 if page == 1 else p2

    url = re.sub(r"<([^,>]*),([^>]*)>", _replace_angle_brackets, url)

    # 替换分页宏
    url = url.replace("{{page}}", str(page))
    url = url.replace("{{page+1}}", str(page + 1))
    url = url.replace("{{page-1}}", str(max(0, page - 1)))
    url = url.replace("{{(page-1)*10}}", str((page - 1) * 10))
    url = url.replace("{{(page-1)*20}}", str((page - 1) * 20))
    url = url.replace("{{(page-1)*50}}", str((page - 1) * 50))
    url = re.sub(r"\{\{.*?\}\}", str(page), url)

    if base_url and not (url.startswith("http://") or url.startswith("https://")):
        url = urljoin(base_url, url)

    return url


def crawl_explore_books(
    source_id: int,
    explore_url: str,
    page: int = 1,
    timeout: int = 20,
) -> list[dict]:
    """抓取并解析指定书源的探索/分类列表页书籍。"""
    src = source_by_id(source_id)
    if not src:
        raise ValueError(f"书源 (ID:{source_id}) 不存在")

    raw_rule = json.loads(src["rule"]) if src.get("rule") else {}
    base_url = raw_rule.get("bookSourceUrl") or src.get("url") or ""
    rule_exp = raw_rule.get("ruleExplore") or {}
    rule_search = raw_rule.get("ruleSearch") or {}

    rule_merged = dict(rule_search)
    rule_merged.update({k: v for k, v in rule_exp.items() if v})

    target_url = resolve_explore_url(explore_url, page=page, base_url=base_url)
    if not target_url:
        raise ValueError("无效的探索目标地址")

    src_label = f"{src['name']} (ID:{source_id})"
    logger.info("[探索抓取] [%s] 开始抓取探索分类第 %d 页 -> %s", src_label, page, target_url)

    html = fetch_url(target_url, timeout=timeout, base_url=base_url, context=f"探索:{src['name']}")
    if not html:
        return []

    # 1. 尝试 JSON 解析
    s_trim = html.strip()
    is_json = False
    data = None
    if (s_trim.startswith("{") and s_trim.endswith("}")) or (s_trim.startswith("[") and s_trim.endswith("]")):
        try:
            data = json.loads(s_trim)
            is_json = True
        except Exception:
            is_json = False

    if is_json and data is not None:
        book_list_field = str(rule_merged.get("bookList", "")).replace("$.", "").strip()
        items_data = []
        if isinstance(data, list):
            items_data = data
        elif isinstance(data, dict):
            if book_list_field and book_list_field in data:
                items_data = data[book_list_field]
            elif "data" in data and isinstance(data["data"], list):
                items_data = data["data"]
            elif "list" in data and isinstance(data["list"], list):
                items_data = data["list"]
            elif "books" in data and isinstance(data["books"], list):
                items_data = data["books"]

        books = []
        for item in items_data:
            if not isinstance(item, dict):
                continue
            name_key = str(rule_merged.get("name", "name")).replace("$.", "").strip()
            author_key = str(rule_merged.get("author", "author")).replace("$.", "").strip()
            cover_key = str(rule_merged.get("coverUrl", rule_merged.get("cover", "cover"))).replace("$.", "").strip()
            intro_key = str(rule_merged.get("intro", "intro")).replace("$.", "").strip()
            kind_key = str(rule_merged.get("kind", "kind")).replace("$.", "").strip()
            burl_rule = str(rule_merged.get("bookUrl", "")).strip()

            name = str(item.get(name_key) or item.get("book_name") or item.get("title") or item.get("name") or "").strip()
            author = str(item.get(author_key) or item.get("author") or "").strip()
            cover = str(item.get(cover_key) or item.get("thumb_url") or item.get("cover") or "").strip()
            intro = str(item.get(intro_key) or item.get("abstract") or item.get("desc") or item.get("intro") or "").strip()
            kind = str(item.get(kind_key) or item.get("category") or "").strip()

            burl = burl_rule
            for k, v in item.items():
                burl = burl.replace(f"{{{{$.{k}}}}}", str(v)).replace(f"{{{{{k}}}}}", str(v))
            if not burl or burl == burl_rule:
                burl = str(item.get("bookUrl") or item.get("url") or item.get("book_url") or "")
            if base_url and burl and not (burl.startswith("http://") or burl.startswith("https://")):
                burl = urljoin(base_url, burl)

            if name:
                books.append({
                    "name": name,
                    "author": author,
                    "cover": cover,
                    "intro": intro,
                    "kind": kind,
                    "book_url": burl,
                    "source_id": source_id,
                    "source_name": src["name"],
                })

        logger.info("[探索抓取] [%s] JSON 解析完成，获取到 %d 本书籍", src_label, len(books))
        return books

    # 2. HTML DOM 解析
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    book_list_rule = rule_merged.get("bookList")
    if not book_list_rule:
        logger.warning("[探索抓取] [%s] 缺少 bookList 选择器", src_label)
        return []

    nodes = safe_select(soup, book_list_rule)
    books = []
    for node in nodes:
        name = extract_value(node, rule_merged.get("name") or "text", base_url).strip()
        author = extract_value(node, rule_merged.get("author") or "", base_url).strip()
        cover = extract_value(node, rule_merged.get("coverUrl") or rule_merged.get("cover") or "", base_url).strip()
        intro = extract_value(node, rule_merged.get("intro") or "", base_url).strip()
        kind = extract_value(node, rule_merged.get("kind") or "", base_url).strip()
        word_count = extract_value(node, rule_merged.get("wordCount") or "", base_url).strip()
        last_chapter = extract_value(node, rule_merged.get("lastChapter") or "", base_url).strip()
        burl = extract_value(node, normalize_extract_rule(rule_merged.get("bookUrl") or "", "a@href"), base_url).strip()

        if name or burl:
            books.append({
                "name": name,
                "author": author,
                "cover": cover,
                "intro": intro,
                "kind": kind,
                "word_count": word_count,
                "last_chapter": last_chapter,
                "book_url": burl,
                "source_id": source_id,
                "source_name": src["name"],
            })

    logger.info("[探索抓取] [%s] HTML 解析完成，获取到 %d 本书籍", src_label, len(books))
    return books
