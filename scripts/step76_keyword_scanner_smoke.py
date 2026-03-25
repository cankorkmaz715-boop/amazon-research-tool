#!/usr/bin/env python3
"""Step 76: Keyword scanner v1 – search fetch, multi-page scan, ASIN extraction, deduplication, ASIN pool."""
import os
import sys
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.browser import BrowserSession
    from amazon_research.crawler import scan_keyword

    fixture_path = os.path.join(ROOT, "scripts", "fixtures", "sample_listing.html")
    file_url = "file://" + os.path.abspath(fixture_path)

    session = BrowserSession(headless=True)
    session.start()
    try:
        with patch("amazon_research.crawler.keyword_scanner.get_search_url", return_value=file_url):
            pool = scan_keyword(session, "fixture_test", marketplace="DE", max_pages=2)

        search_fetch_ok = pool is not None and "asins" in pool and "pages_scanned" in pool
        multi_page_ok = (
            pool.get("pages_scanned", 0) >= 1
            and "urls" in pool
            and isinstance(pool["urls"], list)
            and len(pool["urls"]) >= 1
        )
        asins = pool.get("asins") or []
        asin_ok = isinstance(asins, list) and len(asins) >= 1
        dedupe_ok = len(asins) == len(set(asins))
        pool_ok = (
            pool.get("pool_size") == len(asins)
            and "keyword" in pool
            and "marketplace" in pool
            and pool.get("marketplace") == "DE"
        )
    finally:
        session.close()

    print("keyword scanner v1 OK")
    print("search fetch: OK" if search_fetch_ok else "search fetch: FAIL")
    print("multi-page scan: OK" if multi_page_ok else "multi-page scan: FAIL")
    print("asin extraction: OK" if asin_ok else "asin extraction: FAIL")
    print("deduplication: OK" if dedupe_ok else "deduplication: FAIL")
    print("asin pool ready: OK" if pool_ok else "asin pool ready: FAIL")

    if not (search_fetch_ok and multi_page_ok and asin_ok and dedupe_ok and pool_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
