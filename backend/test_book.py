from book import parse_chapters
from epub import html_to_text as epub_html_to_text


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
