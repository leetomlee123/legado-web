import json
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import db
import source

def test_single_source(src_row):
    src_id = src_row["id"]
    src_name = src_row["name"]
    src_url = src_row["url"]
    rule_raw = src_row["rule"]

    res = {
        "id": src_id,
        "name": src_name,
        "url": src_url,
        "search_ok": False,
        "search_count": 0,
        "search_err": None,
        "explore_ok": False,
        "explore_count": 0,
        "explore_err": None,
        "toc_ok": False,
        "toc_count": 0,
        "toc_err": None,
        "content_ok": False,
        "content_len": 0,
        "content_err": None,
    }

    try:
        rule_data = json.loads(rule_raw)
    except Exception as e:
        res["search_err"] = f"JSON解析失败: {e}"
        return res

    check_keyword = rule_data.get("ruleSearch", {}).get("checkKeyWord") or rule_data.get("checkKeyWord") or "修仙"

    parsed_rule = None
    try:
        parsed_rule = source.parse_legado_rule(rule_raw)
    except Exception as e:
        res["search_err"] = f"规则编译失败: {e}"
        return res

    found_books = []

    # 1. 测试搜索
    if parsed_rule and parsed_rule.search and parsed_rule.search.url:
        try:
            html, final_url = source.fetch_search_response(
                parsed_rule.search.url,
                check_keyword,
                timeout=12,
                base_url=parsed_rule.base_url,
                source_name=src_name,
                source_id=src_id,
            )
            found_books = source.crawl_search(
                html,
                parsed_rule.search,
                final_url,
                source_name=src_name,
                source_id=src_id,
            )
            if found_books:
                res["search_ok"] = True
                res["search_count"] = len(found_books)
            else:
                res["search_err"] = f"搜索未匹配到书籍 (关键词: {check_keyword})"
        except Exception as e:
            res["search_err"] = str(e)[:120]

    # 2. 测试探索 (如果存在 exploreUrl)
    explore_url_str = rule_data.get("exploreUrl")
    if explore_url_str:
        try:
            explore_items = source.parse_explore_items(explore_url_str)
            if explore_items:
                target_exp_url = explore_items[0].get("url")
                if target_exp_url:
                    exp_books = source.crawl_explore_books(src_id, target_exp_url, page=1)
                    if exp_books:
                        res["explore_ok"] = True
                        res["explore_count"] = len(exp_books)
                        if not found_books:
                            found_books = exp_books
                    else:
                        res["explore_err"] = "探索返回空书籍列表"
        except Exception as e:
            res["explore_err"] = str(e)[:120]

    # 3. 测试目录 TOC
    sample_book = found_books[0] if found_books else None
    sample_chapter = None
    book_dict = None
    if sample_book and parsed_rule and parsed_rule.toc:
        try:
            book_url = sample_book.get("bookUrl") or sample_book.get("book_url") or sample_book.get("source_url") or ""
            book_dict = {
                "id": 99999,
                "name": sample_book.get("name") or "测试书籍",
                "author": sample_book.get("author") or "",
                "source_id": src_id,
                "source_url": book_url,
            }
            if book_url:
                real_toc_url, detail_html = source._resolve_toc_url(book_dict, parsed_rule, book_dict["name"])
                chapters = source.fetch_all_toc(
                    real_toc_url,
                    parsed_rule.toc,
                    source_name=src_name,
                    source_id=src_id,
                    book_name=book_dict["name"],
                    initial_html=detail_html,
                )
                if chapters:
                    res["toc_ok"] = True
                    res["toc_count"] = len(chapters)
                    sample_chapter = chapters[0]
                else:
                    res["toc_err"] = "目录解析返回空列表"
            else:
                res["toc_err"] = "搜索或探索结果缺少书籍链接 (bookUrl)"
        except Exception as e:
            res["toc_err"] = str(e)[:120]

    # 4. 测试正文 Content
    if sample_chapter and book_dict:
        try:
            ch_url = sample_chapter.get("chapterUrl") or sample_chapter.get("url") or ""
            ch_title = sample_chapter.get("title") or ""
            if ch_url:
                content = source.fetch_web_chapter(book_dict, ch_url, ch_title)
                if content and len(content.strip()) >= 50:
                    res["content_ok"] = True
                    res["content_len"] = len(content.strip())
                else:
                    res["content_err"] = f"正文过短 ({len(content.strip()) if content else 0} 字符)"
        except Exception as e:
            res["content_err"] = str(e)[:120]

    return res


def main():
    conn = db.open_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, url, rule FROM book_source WHERE enabled = 1 ORDER BY id ASC")
    rows = cursor.fetchall()
    total = len(rows)
    print(f"==================================================")
    print(f"  开始依次测试 {total} 个已导入书源的规则解析与抓取能力")
    print(f"==================================================")

    results = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(test_single_source, dict(r)): r["id"] for r in rows}
        done_cnt = 0
        for f in as_completed(futures):
            done_cnt += 1
            res = f.result()
            results.append(res)
            status_search = "✓" if res["search_ok"] else "✗"
            status_toc = "✓" if res["toc_ok"] else "-"
            status_content = "✓" if res["content_ok"] else "-"
            status_exp = "✓" if res["explore_ok"] else "-"
            print(f"[{done_cnt:3d}/{total:3d}] (ID:{res['id']:3d}) {res['name']:<14} | 搜:{status_search}({res['search_count']}) 探:{status_exp}({res['explore_count']}) 目:{status_toc}({res['toc_count']}) 文:{status_content}({res['content_len']}字)")

    elapsed = time.time() - t0
    print(f"\n==================================================")
    print(f"  测试完成！耗时: {elapsed:.2f}s")
    print(f"==================================================")

    search_success = sum(1 for r in results if r["search_ok"])
    explore_success = sum(1 for r in results if r["explore_ok"])
    toc_success = sum(1 for r in results if r["toc_ok"])
    content_success = sum(1 for r in results if r["content_ok"])

    print(f"统计概要:")
    print(f"  - 搜索成功: {search_success}/{total} ({search_success/total*100:.1f}%)")
    print(f"  - 探索成功: {explore_success}/{total} ({explore_success/total*100:.1f}%)")
    print(f"  - 目录解析成功: {toc_success}/{total}")
    print(f"  - 正文解析成功: {content_success}/{total}")

    with open("/root/gits/legado-web/backend/diagnose_results.json", "w", encoding="utf-8") as fp:
        json.dump(results, fp, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
