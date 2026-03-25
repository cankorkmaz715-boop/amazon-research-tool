"""
Playwright browser session. Single place for launch, context, and page.
Anti-bot: randomized delays between actions, goto with retry and exponential backoff.
Proxy from central ProxyManager; timeouts from config. No scraping logic here.
"""
import random
import time
from typing import Any, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("browser")


class BrowserSession:
    """
    Playwright Chromium session. Use as context manager or call start() / close().
    Injects proxy from ProxyManager when enabled; applies timeout from config.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: Optional[int] = None,
        proxy=None,
    ) -> None:
        self._headless = headless
        if timeout_ms is not None:
            self._timeout_ms = timeout_ms
        else:
            from amazon_research.config import get_config
            self._timeout_ms = get_config().page_load_timeout_ms
        self._proxy = proxy
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def _get_proxy_dict(self) -> Optional[dict]:
        if self._proxy is None:
            from amazon_research.proxy import ProxyManager
            self._proxy = ProxyManager.from_config()
        return self._proxy.get_playwright_proxy() if self._proxy else None

    def start(self) -> None:
        """Launch Chromium and create one page. Safe to call once. Rotates proxy (if pool) once per session."""
        from playwright.sync_api import sync_playwright

        if self._proxy is None:
            from amazon_research.proxy import ProxyManager
            self._proxy = ProxyManager.from_config()
        if hasattr(self._proxy, "get_next_for_session"):
            self._proxy.get_next_for_session()

        pw = sync_playwright().start()
        self._playwright = pw
        self._browser = pw.chromium.launch(headless=self._headless)

        opts = {
            "viewport": {"width": 1920, "height": 1080},
            "ignore_https_errors": True,
        }
        proxy_dict = self._get_proxy_dict()
        if proxy_dict:
            opts["proxy"] = proxy_dict

        self._context = self._browser.new_context(**opts)
        if self._timeout_ms:
            self._context.set_default_navigation_timeout(self._timeout_ms)
            self._context.set_default_timeout(self._timeout_ms)
        self._page = self._context.new_page()
        logger.info(
            "browser session started",
            extra={"headless": self._headless, "proxy": bool(proxy_dict)},
        )

    def get_page(self):
        """Return the current page. Call start() first."""
        return self._page

    def delay_between_actions(self) -> None:
        """Sleep a random interval (antibot_delay_min_sec – antibot_delay_max_sec). Avoids rapid consecutive loads."""
        from amazon_research.config import get_config
        cfg = get_config()
        sec = random.uniform(cfg.antibot_delay_min_sec, cfg.antibot_delay_max_sec)
        time.sleep(sec)

    def goto_with_retry(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to url with exponential backoff on failure. Raises after last retry."""
        from amazon_research.config import get_config
        cfg = get_config()
        last: Optional[Exception] = None
        for attempt in range(cfg.navigation_retries):
            try:
                self._page.goto(url, wait_until=wait_until)
                return
            except Exception as e:
                last = e
                if attempt < cfg.navigation_retries - 1:
                    backoff = cfg.navigation_retry_base_sec * (2 ** attempt)
                    logger.warning("navigation failed, retry in %s s", backoff, extra={"error": str(e)})
                    time.sleep(backoff)
        if last:
            raise last

    def close(self) -> None:
        """Release browser resources."""
        if self._page:
            try:
                self._page.close()
            except Exception as e:
                logger.warning("page close: %s", e)
            self._page = None
        if self._context:
            try:
                self._context.close()
            except Exception as e:
                logger.warning("context close: %s", e)
            self._context = None
        if self._browser:
            try:
                self._browser.close()
            except Exception as e:
                logger.warning("browser close: %s", e)
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception as e:
                logger.warning("playwright stop: %s", e)
            self._playwright = None

    def __enter__(self) -> "BrowserSession":
        self.start()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
