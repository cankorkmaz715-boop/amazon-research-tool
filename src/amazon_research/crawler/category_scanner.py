"""
Category scanner v1. Step 72 – multi-page category traversal, ASIN deduplication, discovery pool.
Built on category crawler; configurable page limit; queue- and worker-friendly output.
Async wrapper runs sync scan in thread (reuses async crawler foundation).
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .category_crawler import crawl_category_page

logger = get_logger("crawler.category_scanner")


def _derive_market_from_url(url: str) -> str:
    """Step 109: Derive market code from category/listing URL (e.g. amazon.de -> DE). Step 184: AU."""
    u = (url or "").lower()
    if "amazon.de" in u:
        return "DE"
    if "amazon.co.uk" in u:
        return "UK"
    if "amazon.com.au" in u:
        return "AU"
    if "amazon.com" in u and "amazon.co" not in u:
        return "US"
    if "amazon.fr" in u:
        return "FR"
    if "amazon.it" in u:
        return "IT"
    if "amazon.es" in u:
        return "ES"
    return "DE"


def scan_category(
    session: Any,
    start_url: str,
    max_pages: Optional[int] = None,
    marketplace: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Traverse category starting at start_url, crawl up to max_pages pages, deduplicate ASINs.
    Step 109: optional marketplace; when absent, derived from start_url. Returns pool with marketplace.
    """
    if max_pages is None:
        from amazon_research.config import get_config
        cfg = get_config()
        max_pages = max(1, min(cfg.max_discovery_pages, cfg.max_discovery_pages_cap))
    max_pages = max(1, max_pages)
    market = (marketplace or "").strip().upper() or _derive_market_from_url(start_url)
    if not market:
        market = "DE"

    seen: set = set()
    urls_visited: List[str] = []
    url = start_url.strip()
    pages_scanned = 0

    while pages_scanned < max_pages and url:
        result = crawl_category_page(session, url, page_index=pages_scanned)
        urls_visited.append(url)
        pages_scanned += 1
        for asin in result.get("asins") or []:
            if asin and asin not in seen:
                seen.add(asin)
        next_url = result.get("next_page_url")
        if not next_url or next_url == url:
            break
        if hasattr(session, "delay_between_actions"):
            session.delay_between_actions()
        url = next_url

    asins = sorted(seen)
    pool = {
        "asins": asins,
        "pool_size": len(asins),
        "pages_scanned": pages_scanned,
        "urls": urls_visited,
        "marketplace": market,
    }
    logger.info(
        "category_scanner done",
        extra={"start_url": start_url[:80], "pages_scanned": pages_scanned, "pool_size": len(asins)},
    )
    return pool


async def scan_category_async(
    start_url: str,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Async category scan: runs scan_category in a thread so sync Playwright is not in the event loop.
    Creates and closes its own browser session inside the thread.
    """
    def _sync() -> Dict[str, Any]:
        from amazon_research.browser import BrowserSession
        session = BrowserSession(headless=True)
        session.start()
        try:
            return scan_category(session, start_url, max_pages=max_pages)
        finally:
            session.close()

    return await asyncio.to_thread(_sync)
