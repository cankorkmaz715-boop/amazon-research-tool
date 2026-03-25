"""
Keyword scanner v1. Step 76 – multi-page search traversal, ASIN deduplication, discovery pool.
Built on keyword crawler; configurable page limit; queue- and worker-friendly output.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.market import get_search_url, get_default_market

from .keyword_crawler import crawl_keyword_page

logger = get_logger("crawler.keyword_scanner")


def scan_keyword(
    session: Any,
    keyword: str,
    marketplace: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Traverse search results starting at keyword, crawl up to max_pages pages, deduplicate ASINs.
    Returns a discovery pool: asins (unique list), pool_size, pages_scanned, urls, keyword, marketplace.
    """
    if max_pages is None:
        from amazon_research.config import get_config
        cfg = get_config()
        max_pages = max(1, min(cfg.max_discovery_pages, cfg.max_discovery_pages_cap))
    max_pages = max(1, max_pages)

    market = (marketplace or get_default_market()).strip().upper() or "DE"
    url = get_search_url(keyword, market)
    seen: set = set()
    urls_visited: List[str] = []
    pages_scanned = 0

    while pages_scanned < max_pages and url:
        result = crawl_keyword_page(session, keyword, marketplace=market, search_url=url)
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
        "keyword": (keyword or "").strip(),
        "marketplace": market,
    }
    logger.info(
        "keyword_scanner done",
        extra={"keyword": (keyword or "")[:50], "pages_scanned": pages_scanned, "pool_size": len(asins)},
    )
    return pool


async def scan_keyword_async(
    keyword: str,
    marketplace: Optional[str] = None,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Async keyword scan: runs scan_keyword in a thread so sync Playwright is not in the event loop.
    Creates and closes its own browser session inside the thread.
    """
    def _sync() -> Dict[str, Any]:
        from amazon_research.browser import BrowserSession
        session = BrowserSession(headless=True)
        session.start()
        try:
            return scan_keyword(session, keyword, marketplace=marketplace, max_pages=max_pages)
        finally:
            session.close()

    return await asyncio.to_thread(_sync)
