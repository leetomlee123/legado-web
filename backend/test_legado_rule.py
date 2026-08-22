import json
from bs4 import BeautifulSoup
from source import (
    safe_select,
    extract_value,
    extract_values,
    convert_jsoup_to_css,
    eval_js_snippet,
    fix_dollar_backref,
)


def test_macro_interpolation():
    html = """
    <div id="info">
      <h1>百炼成神</h1>
      <p>作者：恩赐解脱</p>
      <p>更新时间：2026-08-20</p>
      <p>最新章节：第4000章 大结局</p>
    </div>
    <div id="intro">这是百炼成神的精彩小说简介。最后更新: 2026-08-20</div>
    """
    soup = BeautifulSoup(html, "lxml")

    # 测试多宏拼接与尾随 ## 正则替换
    rule = "&nbsp;&nbsp;\n💮最新章节：{{@@id.info@p.2@text}} | {{@@id.info@p.1@text}}\n📜简介：{{@@id.intro@text}}##[最后更新\\:]*"
    res = extract_value(soup, rule)
    assert "第4000章 大结局" in res
    assert "2026-08-20" in res
    assert "最后更新" not in res


def test_inline_and_postfix_js():
    html = """
    <div class="item">
      <span class="s2"><a href="https://www.xshbook.com/12345/">万古神帝</a></span>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")

    # 1. 测试带 <js> 的 coverUrl 构造
    rule_js = "class.s2@a@href<js>\nvar id = result.match(/(\\d+)/)[1];\n'https://img.example.com/'+id+'.jpg';\n</js>"
    res = extract_value(soup, rule_js)
    assert res == "https://img.example.com/12345.jpg"

    # 2. 测试 @js: 纯 regex 替换快速路径
    rule_replace = "class.s2@a@text@js:result.replace('万古', '无敌')"
    res2 = extract_value(soup, rule_replace)
    assert res2 == "无敌神帝"


def test_jsonpath_extraction():
    data = {
        "status": 200,
        "data": {
            "records": [
                {"bid": 1001, "bName": "大奉打更人", "bAuth": "卖报小郎君", "cat": "仙侠"},
                {"bid": 1002, "bName": "灵境行者", "bAuth": "卖报小郎君", "cat": "科幻"},
            ]
        }
    }

    # 1. 提取列表
    items = extract_values(data, "$.data.records[*].bName")
    assert len(items) == 2
    assert items[0] == "大奉打更人"
    assert items[1] == "灵境行者"

    # 2. 提取并使用 ## 正则
    auth = extract_value(data, "$.data.records[0].bAuth##卖报##大作家")
    assert auth == "大作家小郎君"


def test_multiline_rule_aggregation():
    html = """
    <div class="meta">
      <span class="type">仙侠修真</span>
      <span class="status">连载中</span>
      <span class="words">300万字</span>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")

    rule = ".type@text\n.status@text\n.words@text"
    res = extract_value(soup, rule)
    lines = res.split("\n")
    assert len(lines) == 3
    assert lines[0] == "仙侠修真"
    assert lines[1] == "连载中"
    assert lines[2] == "300万字"


def test_multiclass_and_at_cascade():
    html = """
    <dl class="panel-chapterlist">
      <dd class="col-sm-6 col-md-3 chapter-fa63f2a3">
        <a href="javascript:;" onclick="location.href='/tv/51744/578.html'">第五百零三章 凌玉灵</a>
      </dd>
    </dl>
    """
    soup = BeautifulSoup(html, "lxml")

    nodes = safe_select(soup, "class.col-sm-6 col-md-3 chapter-fa63f2a3@a")
    assert len(nodes) == 1

    rule = "onclick##.+'(.+)'##$1###"
    url = extract_value(nodes[0], rule, base_url="https://www.lysw1.com/tv/51744/6/")
    assert url == "https://www.lysw1.com/tv/51744/578.html"


def test_fallback_and_slice():
    html = """
    <div class="list">
      <p class="opt">备用选项1</p>
      <p class="opt">备用选项2</p>
    </div>
    """
    soup = BeautifulSoup(html, "lxml")

    # || fallback
    res = extract_value(soup, ".non-existent@text || .opt.0@text")
    assert res == "备用选项1"

    # 切片
    items = extract_values(soup, ".opt[1:]@text")
    assert len(items) == 1
    assert items[0] == "备用选项2"


if __name__ == "__main__":
    test_macro_interpolation()
    test_inline_and_postfix_js()
    test_jsonpath_extraction()
    test_multiline_rule_aggregation()
    test_multiclass_and_at_cascade()
    test_fallback_and_slice()
    print("All test_legado_rule.py comprehensive tests passed!")
