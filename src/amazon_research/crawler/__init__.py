"""
Async crawler foundation v1. Step 68 – async-compatible abstraction; coexists with sync flow.
Step 69: async refresh path. Step 71: category crawler (fetch, extract cards, pagination).
"""

from .async_foundation import (
    AsyncCrawlerProtocol,
    get_async_crawler,
    run_discovery_async,
    run_refresh_async,
)
from .category_crawler import (
    crawl_category_page,
    extract_product_cards,
    fetch_category_page,
    get_next_page_url,
)
from .keyword_crawler import crawl_keyword_page
from .keyword_scanner import scan_keyword, scan_keyword_async
from .category_scanner import (
    scan_category,
    scan_category_async,
)
from .refresh_async import (
    execute_plan_batch_async,
    run_refresh_batch_async,
)

__all__ = [
    "AsyncCrawlerProtocol",
    "crawl_category_page",
    "execute_plan_batch_async",
    "extract_product_cards",
    "fetch_category_page",
    "get_async_crawler",
    "get_next_page_url",
    "crawl_keyword_page",
    "scan_keyword",
    "scan_keyword_async",
    "run_discovery_async",
    "run_refresh_async",
    "run_refresh_batch_async",
    "scan_category",
    "scan_category_async",
]
