"""Google Scholar 爬虫 — 通过 Playwright 搜索学术文献。"""

import re
from typing import List, Dict
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from .browser import safe_goto, random_delay


def search_scholar(page: Page, query: str, num_results: int = 5) -> List[Dict]:
    """执行 Google Scholar 搜索。"""
    url = f"https://scholar.google.com/scholar?q={quote_plus(query)}&hl=en"

    if not safe_goto(page, url):
        return []

    random_delay(1, 2)
    results = []

    try:
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        for item in soup.select("div.gs_r.gs_or.gs_scl, div.gs_ri"):
            title_el = item.select_one("h3.gs_rt a, h3 a")
            if not title_el:
                title_el = item.select_one("h3.gs_rt")
                if not title_el:
                    continue
            title = title_el.get_text(strip=True)
            url_str = title_el.get("href", "") if title_el.name == "a" else ""

            author_el = item.select_one("div.gs_a")
            authors = ""
            year = ""
            if author_el:
                author_text = author_el.get_text(strip=True)
                authors = author_text
                year_match = re.search(r'\b(19|20)\d{2}\b', author_text)
                if year_match:
                    year = year_match.group()

            snippet_el = item.select_one("div.gs_rs")
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""

            cited_by = 0
            for link in item.select("div.gs_fl a"):
                cite_match = re.search(r'Cited by (\d+)', link.get_text())
                if cite_match:
                    cited_by = int(cite_match.group(1))
                    break

            results.append({
                "title": title, "url": url_str, "snippet": snippet,
                "authors": authors, "year": year, "cited_by": cited_by,
            })

    except Exception as e:
        print(f"  ⚠️  解析 Scholar 结果失败: {e}")

    return results[:num_results]


def search_landfill_scholar(page: Page, name: str, country: str) -> List[Dict]:
    """搜索一个填埋场的学术文献。"""
    queries = [
        f'"{name}" landfill {country} waste management',
        f'"{name}" discarica {country} gas emission',
    ]

    all_results = []
    for query in queries:
        results = search_scholar(page, query, num_results=3)
        all_results.extend(results)
        if results:
            break
        random_delay(3, 5)

    return all_results
