"""浏览器自动检测 — 扫描本机可用浏览器，为多进程搜索提供引擎列表。"""

import os
from pathlib import Path
from typing import List, NamedTuple, Optional


class BrowserSpec(NamedTuple):
    """浏览器规格描述。"""
    engine: str          # playwright 引擎: "chromium", "firefox", "webkit"
    channel: Optional[str]  # chromium channel: "chrome", "msedge", None
    name: str            # 显示名称

# macOS 浏览器检测列表
_MAC_BROWSERS = [
    ("/Applications/Google Chrome.app", "chromium", "chrome", "Chrome"),
    ("/Applications/Google Chrome Canary.app", "chromium", "chrome-canary", "Chrome Canary"),
    ("/Applications/Microsoft Edge.app", "chromium", "msedge", "Edge"),
    ("/Applications/Brave Browser.app", "chromium", "chrome", "Brave"),
    ("/Applications/Vivaldi.app", "chromium", "chrome", "Vivaldi"),
    ("/Applications/Opera.app", "chromium", "chrome", "Opera"),
    ("/Applications/Arc.app", "chromium", "chrome", "Arc"),
    ("/Applications/Firefox.app", "firefox", None, "Firefox"),
]

# Playwright 内置引擎（始终可用）
_BUILTIN = [
    BrowserSpec("chromium", None, "Chromium (内置)"),
    BrowserSpec("webkit", None, "WebKit (Safari引擎)"),
]


def detect_browsers(include_builtin: bool = True) -> List[BrowserSpec]:
    """检测本机所有可用浏览器。

    Returns:
        BrowserSpec 列表，按优先级排序
    """
    found = []

    # 检测系统安装的浏览器
    for app_path, engine, channel, name in _MAC_BROWSERS:
        if os.path.exists(app_path):
            found.append(BrowserSpec(engine, channel, name))

    # 添加内置引擎
    if include_builtin:
        for spec in _BUILTIN:
            # 避免重复（如已检测到 Chrome 就不重复加 Chromium）
            if not any(f.engine == spec.engine and f.channel == spec.channel for f in found):
                found.append(spec)

    return found


def select_browsers(max_workers: int = 3, prefer: str = None) -> List[BrowserSpec]:
    """选择用于并行搜索的浏览器列表。

    Args:
        max_workers: 最大并行数
        prefer: 偏好的浏览器名称（如 "chrome"）

    Returns:
        不超过 max_workers 个浏览器
    """
    all_browsers = detect_browsers()

    if prefer:
        # 把偏好的浏览器排到前面
        preferred = [b for b in all_browsers if prefer.lower() in b.name.lower()]
        others = [b for b in all_browsers if prefer.lower() not in b.name.lower()]
        all_browsers = preferred + others

    # 不同引擎优先（减少指纹重复）
    selected = []
    seen_engines = set()
    for b in all_browsers:
        key = (b.engine, b.channel)
        if key not in seen_engines:
            selected.append(b)
            seen_engines.add(key)
        if len(selected) >= max_workers:
            break

    # 如果不同引擎不够，补充同引擎不同 channel
    if len(selected) < max_workers:
        for b in all_browsers:
            if b not in selected:
                selected.append(b)
            if len(selected) >= max_workers:
                break

    return selected[:max_workers]


def print_detected():
    """打印检测到的浏览器（调试用）。"""
    browsers = detect_browsers()
    print(f"检测到 {len(browsers)} 个可用浏览器:")
    for i, b in enumerate(browsers, 1):
        channel_str = f" (channel: {b.channel})" if b.channel else ""
        print(f"  {i}. [{b.engine}] {b.name}{channel_str}")


if __name__ == "__main__":
    print_detected()
    print(f"\n推荐并行配置（max_workers=3）:")
    for b in select_browsers(3):
        print(f"  - {b.name} ({b.engine})")
