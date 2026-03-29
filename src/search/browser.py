"""浏览器会话管理 — 支持多浏览器实例并行搜索。

每个 BrowserSession 独立管理一个 Playwright 浏览器实例，
支持 Chrome/Chromium/WebKit/Firefox 多引擎。
"""

import time
import random
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext, Playwright

from .browser_detect import BrowserSpec


STORAGE_DIR = str(Path(__file__).parent.parent.parent / "output" / "browser_state")


class BrowserSession:
    """独立的浏览器会话，每个 worker 进程一个实例。"""

    def __init__(self, spec: BrowserSpec = None, headless: bool = True, worker_id: int = 0):
        self.spec = spec or BrowserSpec("chromium", None, "Chromium")
        self.headless = headless
        self.worker_id = worker_id
        self.pw: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._name = f"[W{worker_id}:{self.spec.name}]"

    def start(self):
        """启动浏览器。"""
        self.pw = sync_playwright().start()

        # 根据引擎类型选择启动方式
        launch_args = {
            "headless": self.headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if self.spec.channel:
            launch_args["channel"] = self.spec.channel

        if self.spec.engine == "chromium":
            self.browser = self.pw.chromium.launch(**launch_args)
        elif self.spec.engine == "firefox":
            launch_args.pop("args", None)  # Firefox 不支持 args
            self.browser = self.pw.firefox.launch(**launch_args)
        elif self.spec.engine == "webkit":
            launch_args.pop("args", None)
            self.browser = self.pw.webkit.launch(**launch_args)
        else:
            self.browser = self.pw.chromium.launch(**launch_args)

        # 创建上下文
        ua = self._get_user_agent()
        storage_path = Path(STORAGE_DIR) / f"state_w{self.worker_id}.json"

        ctx_args = {"locale": "en-US", "user_agent": ua}
        if storage_path.exists():
            try:
                ctx_args["storage_state"] = str(storage_path)
            except Exception:
                pass

        self.context = self.browser.new_context(**ctx_args)
        self.page = self.context.new_page()
        return self

    def save_state(self):
        """保存浏览器状态（cookies）。"""
        if self.context:
            storage_path = Path(STORAGE_DIR) / f"state_w{self.worker_id}.json"
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.context.storage_state(path=str(storage_path))
            except Exception:
                pass

    def close(self):
        """关闭浏览器。"""
        try:
            if self.context:
                self.save_state()
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.pw:
                self.pw.stop()
        except Exception:
            pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.close()

    def _get_user_agent(self) -> str:
        """根据引擎类型返回对应的 User-Agent。"""
        uas = {
            "chromium": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "firefox": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0",
            "webkit": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
        }
        return uas.get(self.spec.engine, uas["chromium"])


# ── 工具函数（供搜索脚本调用） ──

def random_delay(min_sec: float = 2.0, max_sec: float = 5.0):
    """模拟人类操作的随机延迟。"""
    time.sleep(random.uniform(min_sec, max_sec))


def batch_delay():
    """批次间较长延迟。"""
    delay = random.uniform(30, 60)
    time.sleep(delay)


def safe_goto(page: Page, url: str, max_retries: int = 3) -> bool:
    """安全导航到 URL。"""
    for attempt in range(max_retries):
        try:
            page.goto(url, timeout=20000, wait_until="domcontentloaded")
            random_delay(1, 2)

            if check_captcha(page):
                print("  ⚠️  验证码！请手动完成...", flush=True)
                for _ in range(60):
                    time.sleep(5)
                    if not check_captcha(page):
                        print("  ✅ 验证码已通过", flush=True)
                        return True
                return False
            return True

        except Exception as e:
            if attempt < max_retries - 1:
                random_delay(3, 8)
    return False


def check_captcha(page: Page) -> bool:
    """检测 Google 验证码。"""
    try:
        content = page.content().lower()
        return any(kw in content for kw in [
            "recaptcha", "unusual traffic", "automated queries",
            "sorry/index", "captcha", "not a robot",
            "detected unusual traffic",
        ])
    except Exception:
        return False


# ── 兼容旧接口 ──

_default_session: Optional[BrowserSession] = None


def create_browser(headless: bool = True) -> Browser:
    """兼容旧接口。"""
    global _default_session
    _default_session = BrowserSession(headless=headless)
    _default_session.start()
    return _default_session.browser


def create_context(browser: Browser) -> BrowserContext:
    """兼容旧接口。"""
    if _default_session:
        return _default_session.context
    return browser.new_context()


def save_state(context: BrowserContext):
    """兼容旧接口。"""
    if _default_session:
        _default_session.save_state()


def close_browser():
    """兼容旧接口。"""
    global _default_session
    if _default_session:
        _default_session.close()
        _default_session = None
