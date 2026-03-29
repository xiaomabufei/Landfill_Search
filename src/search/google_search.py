"""Google Search 爬虫 — 通过 Playwright 执行 Google 搜索并提取结果。"""

from typing import List, Dict
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from .browser import safe_goto, random_delay


def search_google(page: Page, query: str, num_results: int = 10) -> List[Dict]:
    """执行 Google 搜索，返回结果列表。

    Returns:
        [{"title": str, "url": str, "snippet": str}, ...]
    """
    url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}&hl=en"

    if not safe_goto(page, url):
        return []

    random_delay(1, 2)
    results = []

    try:
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")

        # 策略 1: 通过 a > h3 定位搜索结果（适配 2025-2026 Google DOM）
        for h3 in soup.select("a h3"):
            title = h3.get_text(strip=True)
            if not title:
                continue

            link_el = h3.find_parent("a")
            url_str = link_el["href"] if link_el and link_el.get("href") else ""
            if url_str.startswith("/url?q="):
                url_str = url_str.split("/url?q=")[1].split("&")[0]
            if not url_str.startswith("http"):
                continue

            # 向上查找包含摘要的容器
            snippet = ""
            container = h3.find_parent("div", attrs={"data-hveid": True})
            if not container:
                container = h3.find_parent("div", class_=True)
            if container:
                # 搜索容器内的摘要文本
                for selector in ["div.VwiC3b", "div[data-sncf]", "span.aCOpRe", "div.IsZvec"]:
                    snippet_el = container.select_one(selector)
                    if snippet_el:
                        snippet = snippet_el.get_text(strip=True)
                        break
                if not snippet:
                    # fallback: 取容器内去掉标题后的文本
                    full_text = container.get_text(" ", strip=True)
                    if title in full_text:
                        snippet = full_text.split(title, 1)[-1].strip()[:300]

            results.append({"title": title, "url": url_str, "snippet": snippet})

        # 策略 2 (fallback): 旧版 div.g 选择器
        if not results:
            for g in soup.select("div.g"):
                title_el = g.select_one("h3")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link_el = g.select_one("a[href]")
                url_str = link_el["href"] if link_el else ""
                if not url_str.startswith("http"):
                    continue
                snippet = ""
                for sel in ["div.VwiC3b", "div[data-sncf]"]:
                    el = g.select_one(sel)
                    if el:
                        snippet = el.get_text(strip=True)
                        break
                results.append({"title": title, "url": url_str, "snippet": snippet})

    except Exception as e:
        print(f"  ⚠️  解析搜索结果失败: {e}")

    return results[:num_results]


def search_landfill(page: Page, name: str, country: str, indicator: str) -> List[Dict]:
    """针对一个填埋场的一个指标执行搜索。"""
    INDICATOR_QUERIES = {
        "landfill_type": [
            f'"{name}" landfill {country} "sanitary landfill" OR "dump" OR "discarica"',
            f'"{name}" discarica {country} tipo rifiuti',
        ],
        "has_gas_collection": [
            f'"{name}" landfill {country} biogas OR "gas collection" OR "captazione biogas"',
        ],
        "gas_collection_technology": [
            f'"{name}" landfill {country} biogas flaring OR electrification OR "recupero energetico"',
        ],
        "gas_collection_rate": [
            f'"{name}" landfill {country} "gas collection rate" OR "collection efficiency"',
        ],
        "start_year": [
            f'"{name}" landfill {country} "opened" OR "established" OR "anno apertura"',
            f'"{name}" discarica {country} anno apertura costruzione',
        ],
        "final_year": [
            f'"{name}" landfill {country} "closed" OR "closure" OR "chiusura"',
        ],
        "gas_collection_start_year": [
            f'"{name}" landfill {country} biogas "gas collection" installation year',
        ],
        "general_info": [
            f'"{name}" landfill {country} capacity area operator waste',
            f'"{name}" discarica {country} capacità gestore',
        ],
    }

    queries = INDICATOR_QUERIES.get(indicator, [])
    all_results = []

    for query in queries:
        results = search_google(page, query, num_results=5)
        all_results.extend(results)
        if results:
            break
        random_delay(2, 4)

    return all_results


def search_landfill_all(page: Page, name: str, country: str) -> Dict[str, List[Dict]]:
    """搜索一个填埋场的所有指标。"""
    indicators = [
        "landfill_type", "has_gas_collection", "gas_collection_technology",
        "start_year", "final_year", "general_info",
    ]

    results = {}
    for indicator in indicators:
        print(f"    搜索: {indicator}", flush=True)
        results[indicator] = search_landfill(page, name, country, indicator)
        random_delay(3, 6)

    return results
