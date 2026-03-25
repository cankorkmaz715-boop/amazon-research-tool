"""
Category crawler foundation. Step 71 – fetch category page, extract product cards, collect ASINs, pagination.
Queue-friendly output; integrates with discovery/worker pipeline. Reuses listing parser.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger
from amazon_research.parsers.listing import extract_asins_from_amazon_listing

logger = get_logger("crawler.category_crawler")


def fetch_category_page(session: Any, url: str, wait_until: str = "domcontentloaded") -> Any:
    """
    Navigate to a category/listing URL. Returns the page object from session.
    Caller must have started the session and call get_page() if needed.
    """
    page = session.get_page() if hasattr(session, "get_page") else session
    if not page:
        return None
    session.goto_with_retry(url, wait_until=wait_until)
    return page


def extract_product_cards(page: Any) -> List[Dict[str, Any]]:
    """
    Extract product cards from current listing/category page as list of dicts with at least 'asin'.
    Reuses listing parser (ASINs from links and data-asin). Never crashes.
    """
    if page is None:
        return []
    items = extract_asins_from_amazon_listing(page)
    return items if isinstance(items, list) else []


def get_next_page_url(page: Any, current_url: str) -> Optional[str]:
    """
    Try to find the next page URL (pagination) on the current category/listing page.
    Returns None if no next link. Amazon often uses aria-label='Next' or .s-pagination-next.
    """
    if page is None:
        return None
    try:
        next_href = page.evaluate("""() => {
            const next = document.querySelector('a.s-pagination-next[href], a[aria-label="Next page"][href], .s-pagination-item.s-pagination-next a[href]');
            return next ? next.href : null;
        }""")
        if next_href and isinstance(next_href, str) and next_href.strip():
            return next_href.strip()
    except Exception as e:
        logger.debug("get_next_page_url failed: %s", e)
    return None


def crawl_category_page(
    session: Any,
    url: str,
    page_index: int = 0,
) -> Dict[str, Any]:
    """
    Fetch one category page, extract product cards (ASINs), and detect next page URL.
    Queue-friendly: returns asins list and next_page_url for pagination or follow-up jobs.
    """
    try:
        from amazon_research.monitoring import record_crawler_request
        record_crawler_request()
    except Exception:
        pass
    page = fetch_category_page(session, url)
    if page is None:
        try:
            from amazon_research.monitoring import record_crawler_success
            record_crawler_success()
        except Exception:
            pass
        return {
            "asins": [],
            "items": [],
            "next_page_url": None,
            "page_url": url,
            "page_index": page_index,
        }
    items = extract_product_cards(page)
    asins = [item.get("asin") for item in items if item.get("asin")]
    next_page_url = get_next_page_url(page, url)
    out = {
        "asins": asins,
        "items": items,
        "next_page_url": next_page_url,
        "page_url": url,
        "page_index": page_index,
    }
    logger.info(
        "category_crawler page",
        extra={"url": url[:80], "asins_count": len(asins), "has_next": bool(next_page_url)},
    )
    try:
        from amazon_research.monitoring import record_crawler_success
        record_crawler_success()
    except Exception:
        pass
    return out
