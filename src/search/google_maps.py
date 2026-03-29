"""Google Maps 爬虫 — 通过 Playwright 确认填埋场位置和运营状态。"""

import re
from typing import Dict, Optional
from urllib.parse import quote_plus

from playwright.sync_api import Page

from .browser import safe_goto, random_delay


def search_maps(page: Page, query: str, lat: float = None, lng: float = None) -> Optional[Dict]:
    """搜索 Google Maps，返回地点信息。"""
    if lat and lng:
        url = f"https://www.google.com/maps/search/{quote_plus(query)}/@{lat},{lng},13z"
    else:
        url = f"https://www.google.com/maps/search/{quote_plus(query)}"

    if not safe_goto(page, url):
        return None

    # Maps 是 SPA，等待加载
    random_delay(3, 5)

    result = {}
    try:
        # 等待主内容加载
        try:
            page.wait_for_selector("div[role='main'], div[role='feed']", timeout=10000)
        except Exception:
            return None

        # 地点名称
        for selector in ["h1.DUwDvf", "h1.fontHeadlineLarge", "h1"]:
            el = page.query_selector(selector)
            if el:
                result["name"] = el.inner_text().strip()
                break

        # 地址
        el = page.query_selector("button[data-item-id='address'] div.fontBodyMedium, div.rogA2c")
        if el:
            result["address"] = el.inner_text().strip()

        # 运营状态
        for selector in ["span.ZDu9vd", "span.o0Svhf"]:
            el = page.query_selector(selector)
            if el:
                status_text = el.inner_text().strip().lower()
                if "closed" in status_text or "chiuso" in status_text:
                    result["status"] = "closed"
                elif "open" in status_text or "aperto" in status_text:
                    result["status"] = "operational"
                else:
                    result["status"] = status_text
                break

        # 地点类型
        el = page.query_selector("button[jsaction*='category'] span, span.DkEaL")
        if el:
            result["place_type"] = el.inner_text().strip()

        # 从 URL 提取坐标
        current_url = page.url
        coord_match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', current_url)
        if coord_match:
            result["map_lat"] = float(coord_match.group(1))
            result["map_lng"] = float(coord_match.group(2))

    except Exception as e:
        print(f"  ⚠️  解析 Maps 结果失败: {e}")
        return None

    return result if result else None


def search_landfill_maps(page: Page, name: str, country: str,
                          lat: float = None, lng: float = None) -> Optional[Dict]:
    """搜索一个填埋场在 Google Maps 上的信息。"""
    queries = [
        f"{name} landfill {country}",
        f"{name} discarica {country}",
        f"discarica {name}",
    ]

    for query in queries:
        result = search_maps(page, query, lat=lat, lng=lng)
        if result and result.get("name"):
            return result
        random_delay(2, 4)

    return None
