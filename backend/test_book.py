from bs4 import BeautifulSoup
from book import parse_chapters
from epub import html_to_text as epub_html_to_text
from source import (
    convert_jsoup_to_css,
    safe_select,
    extract_values,
    apply_replace_regex,
    is_same_chapter_subpage,
    extract_next_content_url,
    parse_legado_rule,
)


def test_parse_chapters():
    text = "前言内容\n第一章 开始\n正文甲\n第二章 继续\n正文乙"
    chs = parse_chapters(text)
    assert len(chs) == 3, chs
    assert chs[0]["title"] == "序言" and chs[0]["content"] == "前言内容"
    assert chs[1]["title"] == "第一章 开始" and chs[1]["content"] == "正文甲"
    assert chs[2]["title"] == "第二章 继续" and chs[2]["content"] == "正文乙"


def test_parse_chapters_fallback():
    chs = parse_chapters("没有章节标题的一整本书")
    assert len(chs) == 1 and chs[0]["title"] == "正文"


def test_html_to_text():
    got = epub_html_to_text("<p>你好</p><br/><div>世界</div>")
    assert got in ("你好\n\n世界", "你好\n世界"), got


def test_jsoup_selector_conversion():
    assert convert_jsoup_to_css("class.content") == ".content"
    assert convert_jsoup_to_css("id.pb_next") == "#pb_next"
    assert convert_jsoup_to_css("tag.a") == "a"
    assert convert_jsoup_to_css("id.info tag.p") == "#info p"


def test_selector_pos_slice_excl():
    html = "<div><p>p0</p><p>p1</p><p>p2</p><p>p3</p></div>"
    soup = BeautifulSoup(html, "html.parser")
    res = safe_select(soup, "p!0")
    assert [el.get_text() for el in res] == ["p1", "p2", "p3"]
    res0 = safe_select(soup, "p.0")
    assert [el.get_text() for el in res0] == ["p0"]
    res_slice = safe_select(soup, "p[1:]")
    assert [el.get_text() for el in res_slice] == ["p1", "p2", "p3"]


def test_extract_values_cascade_and_xpath():
    html = """
    <div id="info">
      <p class="author">作者：唐家三少</p>
    </div>
    <div class="next-page"><a href="/ch1_2.html">下一页</a></div>
    <select name="page">
      <option value="/ch1.html">第1章</option>
      <option value="/ch2.html">第2章</option>
    </select>
    """
    soup = BeautifulSoup(html, "html.parser")
    v1 = extract_values(soup, "class.next-page@tag.a@href", "https://foo.com/book/1001.html")
    assert v1 == ["https://foo.com/ch1_2.html"]

    v2 = extract_values(soup, "id.info@p.author@text##作者：")
    assert v2 == ["唐家三少"]

    v3 = extract_values(soup, "option@value", "https://foo.com/book/")
    assert v3 == ["https://foo.com/ch1.html", "https://foo.com/ch2.html"]

    v4 = extract_values(soup, '//a[text()="下一页"]/@href', "https://foo.com/book/1001.html")
    assert v4 == ["https://foo.com/ch1_2.html"]


def test_apply_replace_regex():
    raw = "第一章 降临\n天地玄黄，宇宙洪荒。\n(本章完)\n请记住本书首发：xxx.com"
    rule = r"##\(本章完\)|^第.*章\s.*\n|请记住本书首发.*"
    cleaned = apply_replace_regex(raw, rule, "测试书", "第一章 降临")
    assert "(本章完)" not in cleaned
    assert "请记住" not in cleaned
    assert "天地玄黄，宇宙洪荒。" in cleaned


def test_subpage_detection():
    assert is_same_chapter_subpage("https://a.com/123.html", "https://a.com/123_2.html") is True
    assert is_same_chapter_subpage("https://a.com/123_1.html", "https://a.com/123_2.html") is True
    assert is_same_chapter_subpage("https://a.com/123.html?p=1", "https://a.com/123.html?p=2") is True
    assert is_same_chapter_subpage("https://a.com/123.html", "https://a.com/124.html") is False
    assert is_same_chapter_subpage("https://a.com/123_2.html", "https://a.com/124.html") is False


def test_extract_next_content_url_with_js():
    html1 = '<div><a href="/ch1_2.html" id="pb_next">下一页</a></div>'
    html2 = '<div><a href="/ch2.html" id="pb_next">下一页</a></div>'
    rule_js = r"#pb_next@href\n@js:\n/_\d+\.html/.test(result) ? result : \"\";"
    soup1 = BeautifulSoup(html1, "html.parser")
    soup2 = BeautifulSoup(html2, "html.parser")
    assert extract_next_content_url(soup1, "https://example.com/ch1.html", rule_js) == "https://example.com/ch1_2.html"
    assert extract_next_content_url(soup2, "https://example.com/ch1_2.html", rule_js) == ""


def test_parse_legado_rule_with_pagination():
    json_str = """
    {
      "bookSourceName": "测试源",
      "ruleToc": {
        "chapterList": ".list a",
        "chapterName": "text",
        "chapterUrl": "href",
        "nextTocUrl": "option@value"
      },
      "ruleContent": {
        "content": ".content@html",
        "nextContentUrl": "text.下一页@href",
        "replaceRegex": "##\\\\(本章完\\\\)"
      }
    }
    """
    rule = parse_legado_rule(json_str)
    assert rule is not None
    assert rule.toc.next_toc_url == "option@value"
    assert rule.content.next_content_url == "text.下一页@href"
    assert rule.content.replace_regex == r"##\(本章完\)"


def test_m_to_www_conversion():
    from settings import convert_m_to_www, normalize_source_url, set_m_to_www
    assert convert_m_to_www("https://m.biquge.com/123/456.html") == "https://www.biquge.com/123/456.html"
    assert convert_m_to_www("http://m.69shu.com/txt/1.htm") == "http://www.69shu.com/txt/1.htm"
    assert convert_m_to_www("//m.xbiquge.la/book/1/") == "//www.xbiquge.la/book/1/"
    assert convert_m_to_www("m.biquge.com/123") == "www.biquge.com/123"
    assert convert_m_to_www("https://www.biquge.com/123") == "https://www.biquge.com/123"

    set_m_to_www(False)
    assert normalize_source_url("https://m.biquge.com/123") == "https://m.biquge.com/123"
    set_m_to_www(True)
    assert normalize_source_url("https://m.biquge.com/123") == "https://www.biquge.com/123"
    set_m_to_www(False)


def test_js_dynamic_base64_content_preprocessing():
    import base64
    from source import ContentRule, crawl_content_single_page

    raw_html_content = "<p>第一段：天青色等烟雨。</p><p>第二段：而我在等你。</p>"
    encoded_b64 = base64.b64encode(raw_html_content.encode("utf-8")).decode("ascii")

    full_page_html = f"""
    <html>
      <body>
        <div class="readcontent" id="rtext"></div>
        <script>
          (function() {{
            var encoded = "{encoded_b64}";
            function decodeBase64Utf8(base64) {{
              return atob(base64);
            }}
            document.getElementById('rtext').innerHTML = decodeBase64Utf8(encoded);
          }})();
        </script>
      </body>
    </html>
    """

    rule = ContentRule(selector="#rtext p", text="text", next_content_url="", replace_regex="")
    paras = crawl_content_single_page(full_page_html, rule)
    assert len(paras) == 2, paras
    assert paras[0] == "第一段：天青色等烟雨。"
    assert paras[1] == "第二段：而我在等你。"


def test_explore_url_parsing_and_resolution():
    from source import parse_explore_items, resolve_explore_url

    # 1. 测试标准与宽松 JSON 格式
    json_spec = """[
      {"title": "玄幻魔法", "url": "/sort/1/{{page}}/", "style": {"layout_flexGrow": 0.25}},
      {"title": "武侠修真", "url": "/sort/2/{{page}}/", "style": {"layout_flexGrow": 0.25}}
    ]"""
    items = parse_explore_items(json_spec)
    assert len(items) == 2
    assert items[0]["title"] == "玄幻魔法"
    assert items[0]["url"] == "/sort/1/{{page}}/"

    # 2. 测试文本多行与 :: 语法
    text_spec = "玄幻::/sort/1/<,{{page}}.html>\n仙侠::/sort/2/<,{{page}}.html>"
    items2 = parse_explore_items(text_spec)
    assert len(items2) == 2
    assert items2[0]["title"] == "玄幻"
    assert items2[0]["url"] == "/sort/1/<,{{page}}.html>"

    # 3. 测试分页宏解析
    u1 = resolve_explore_url("/sort/1/<,{{page}}.html>", page=1, base_url="https://test.com")
    assert u1 == "https://test.com/sort/1/"
    u2 = resolve_explore_url("/sort/1/<,{{page}}.html>", page=2, base_url="https://test.com")
    assert u2 == "https://test.com/sort/1/2.html"


if __name__ == "__main__":
    test_parse_chapters()
    test_parse_chapters_fallback()
    test_html_to_text()
    test_jsoup_selector_conversion()
    test_selector_pos_slice_excl()
    test_extract_values_cascade_and_xpath()
    test_apply_replace_regex()
    test_subpage_detection()
    test_extract_next_content_url_with_js()
    test_parse_legado_rule_with_pagination()
    test_m_to_www_conversion()
    test_js_dynamic_base64_content_preprocessing()
    test_explore_url_parsing_and_resolution()
    print("All test_book.py tests passed successfully!")

