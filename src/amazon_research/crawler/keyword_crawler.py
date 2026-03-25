"""
Keyword crawler foundation. Step 75 – accept keyword, build search URL, fetch results, extract ASINs.
Compatible with category crawler/scanner; queue-friendly output. Reuses listing parser.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.market import get_search_url, get_default_market

from .category_crawler import fetch_category_page, extract_product_cards, get_next_page_url

logger = get_logger("crawler.keyword_crawler")


def crawl_keyword_page(
    session: Any,
    keyword: str,
    marketplace: Optional[str] = None,
    search_url: Optional[str] = None,
    wait_until: str = "domcontentloaded",
) -> Dict[str, Any]:
    """
    Fetch a search results page (search_url or build from keyword/marketplace), extract product cards (ASINs).
    Returns queue-friendly dict: asins, items, keyword, marketplace, search_url, next_page_url (for pagination).
    """
    try:
        from amazon_research.monitoring import record_crawler_request
        record_crawler_request()
    except Exception:
        pass
    market = (marketplace or get_default_market()).strip().upper() or "DE"
    url = (search_url or get_search_url(keyword, market)).strip()
    page = fetch_category_page(session, url, wait_until=wait_until)
    if page is None:
        try:
            from amazon_research.monitoring import record_crawler_success
            record_crawler_success()
        except Exception:
            pass
        return {
            "asins": [],
            "items": [],
            "keyword": (keyword or "").strip(),
            "marketplace": market,
            "search_url": url,
            "next_page_url": None,
        }
    items = extract_product_cards(page)
    asins = [item.get("asin") for item in items if item.get("asin")]
    next_page_url = get_next_page_url(page, url)
    out = {
        "asins": asins,
        "items": items,
        "keyword": (keyword or "").strip(),
        "marketplace": market,
        "search_url": url,
        "next_page_url": next_page_url,
    }
    logger.info(
        "keyword_crawler page",
        extra={"keyword": (keyword or "")[:50], "marketplace": market, "asins_count": len(asins)},
    )
    try:
        from amazon_research.monitoring import record_crawler_success
        record_crawler_success()
    except Exception:
        pass
    return out
