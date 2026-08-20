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


def fetch_url(url: str, timeout: float = 20, base_url: str = "") -> str:
    url = (url or "").strip()
    if base_url and not (url.startswith("http://") or url.startswith("https://")):
        url = urljoin(base_url, url)
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError(f"无效的请求地址: {url}")

    resp = cffi_requests.get(
        url,
        impersonate="chrome120",
        timeout=timeout,
        headers={"User-Agent": UA},
        allow_redirects=True,
        proxy=get_proxy() or None,
        verify=False,
    )
    resp.raise_for_status()
    return decode_http_response(resp)


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


@dataclass
class ContentRule:
    selector: str = ""
    text: str = ""


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


def _strip_js_pos_and_slice(selector: str) -> tuple[str, int | None, tuple[int | None, int | None] | None]:
    """
    处理 Legado 3.0 选择器末尾的位置下标与切片：
    例如：
      .author.0        -> ('.author', 0, None)
      div#info > p.0   -> ('div#info > p', 0, None)
      div.con_top > a.1-> ('div.con_top > a', 1, None)
      dd[9:]           -> ('dd', None, (9, None))
      dd[0]            -> ('dd', 0, None)
    """
    s = (selector or "").strip()
    if not s:
        return "", None, None

    # 1. 检查方括号切片 [9:] 或 [0]
    slice_m = re.search(r"\[(-?\d*):?(-?\d*)\]\s*$", s)
    if slice_m:
        base = s[: slice_m.start()].strip()
        s1, s2 = slice_m.group(1), slice_m.group(2)
        if ":" in slice_m.group(0):
            start = int(s1) if s1 else None
            stop = int(s2) if s2 else None
            return base, None, (start, stop)
        else:
            return base, int(s1) if s1 else None, None

    # 2. 检查末尾 `.N` 或 `.-N`
    pos_m = re.search(r"\.(-?\d{1,3})\s*$", s)
    if pos_m:
        base = s[: pos_m.start()].strip()
        return base, int(pos_m.group(1)), None

    return s, None, None


def safe_select(el: Tag, selector: str) -> list[Tag]:
    if not (selector or "").strip():
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

    base, pos_idx, slice_args = _strip_js_pos_and_slice(selector)
    try:
        found = list(el.select(base)) if base else [el]
    except Exception:
        return []

    if slice_args is not None:
        start, stop = slice_args
        return found[slice(start, stop)]

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


def fetch_search_response(search_spec: str, keyword: str, timeout: int = 15, base_url: str = "") -> tuple[str, str]:
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

    spec = extract_legado_search_url_spec(search_spec, base_url)
    if not spec:
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
        raise ValueError(f"无效的书源搜索地址: {target_url or search_spec}")

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    if "headers" in options and isinstance(options["headers"], dict):
        req_headers.update(options["headers"])

    raw_body = options.get("body")

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

        resp = cffi_requests.post(
            target_url,
            data=post_data,
            headers=req_headers,
            impersonate="chrome120",
            timeout=timeout,
            proxy=get_proxy() or None,
            verify=False,
        )
    else:
        # GET 请求
        if "?" not in target_url and ("{{key}}" not in search_spec and "{search}" not in search_spec):
            target_url = f"{target_url}?keyword={esc}"
        resp = cffi_requests.get(
            target_url,
            headers=req_headers,
            impersonate="chrome120",
            timeout=timeout,
            proxy=get_proxy() or None,
            verify=False,
        )

    content = resp.content
    try:
        if charset in ("GBK", "GB2312", "GB18030"):
            html = content.decode(charset.lower(), errors="replace")
        else:
            html = resp.text
            if "charset=gbk" in html.lower() or "charset=gb2312" in html.lower():
                html = content.decode("gbk", errors="replace")
    except Exception:
        html = resp.text

    return html, str(resp.url or target_url)


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

    # 分离基础规则与 ## 正则替换部分
    parts = rule.split("##")
    base_rule = parts[0].strip()
    replacements = parts[1:]

    def _attr(target: Tag, attr: str) -> str:
        attr = attr.strip()
        if attr in ("text", "textN", "textNodes", "ownText"):
            return target.get_text(separator="", strip=True)
        if attr == "html":
            return "".join(str(c) for c in target.contents).strip()
        v = target.get(attr) or ""
        if isinstance(v, list):
            v = v[0] if v else ""
        return abs_url(base_url, str(v).strip())

    val = ""
    # 1. @attr 提取
    if "@" in base_rule:
        css, attr = base_rule.rsplit("@", 1)
        css, attr = css.strip(), attr.strip()
        target: Tag | None = el
        if css:
            target = safe_select_one(el, css)
        if target is not None:
            val = _attr(target, attr)
    # 2. 特殊纯文本/HTML提取
    elif base_rule in ("text", "textN", "textNodes", "ownText", ""):
        val = el.get_text(separator="", strip=True)
    elif base_rule == "html":
        val = "".join(str(c) for c in el.contents).strip()
    # 3. 普通 CSS 选择器 fallback
    else:
        found = safe_select_one(el, base_rule)
        val = found.get_text(separator="", strip=True) if found is not None else ""

    # 执行 ## 正则替换
    val = str(val)
    for i in range(0, len(replacements), 2):
        pattern = replacements[i]
        repl = replacements[i + 1] if i + 1 < len(replacements) else ""
        try:
            val = re.sub(pattern, repl, val)
        except Exception:
            pass

    return val.strip()


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
    seen = set()
    root = soup if isinstance(soup, Tag) else soup
    for s in safe_select(root, rule.selector):
        title = extract_value(s, _or_default(rule.title, "text"), base_url).strip()
        url = extract_value(
            s, normalize_extract_rule(rule.chapter_url, "@href"), base_url
        ).strip()
        if not title and not url:
            continue
        key = url if url else title
        if key in seen:
            continue
        seen.add(key)
        out.append({"title": title, "chapterUrl": url})
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
    elems = safe_select(root, rule.selector)
    if not elems:
        return ""
    paragraphs = []
    for el in elems:
        p_text = extract_value(el, _or_default(rule.text, "text"), "")
        if p_text:
            paragraphs.append(p_text)
    return "\n".join(paragraphs)


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
