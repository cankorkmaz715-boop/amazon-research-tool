#!/usr/bin/env python3
"""Step 75: Keyword crawler foundation – search URL build, page fetch, product cards, ASIN discovery, queue integration."""
import os
import sys
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.market import get_search_url
    from amazon_research.crawler import crawl_keyword_page
    from amazon_research.browser import BrowserSession

    # --- Search URL build: marketplace-specific URL with encoded keyword ---
    url_de = get_search_url("wireless mouse", "DE")
    url_uk = get_search_url("test query", "UK")
    search_url_ok = (
        "amazon.de" in url_de
        and "s" in url_de
        and "k=" in url_de
        and "amazon.co.uk" in url_uk
    )

    # Use file fixture for fetch/extract/ASIN so we don't need network
    fixture_path = os.path.join(ROOT, "scripts", "fixtures", "sample_listing.html")
    file_url = "file://" + os.path.abspath(fixture_path)

    session = BrowserSession(headless=True)
    session.start()
    try:
        with patch("amazon_research.crawler.keyword_crawler.get_search_url", return_value=file_url):
            result = crawl_keyword_page(session, "fixture_test", marketplace="DE")
        page_fetch_ok = result is not None and "search_url" in result
        product_card_ok = "items" in result and isinstance(result["items"], list)
        asin_ok = "asins" in result and isinstance(result["asins"], list) and len(result["asins"]) >= 1
        queue_ok = (
            "keyword" in result
            and "marketplace" in result
            and result.get("marketplace") == "DE"
            and "asins" in result
            and "search_url" in result
        )
    finally:
        session.close()

    print("keyword crawler foundation OK")
    print("search url build: OK" if search_url_ok else "search url build: FAIL")
    print("page fetch: OK" if page_fetch_ok else "page fetch: FAIL")
    print("product card extraction: OK" if product_card_ok else "product card extraction: FAIL")
    print("asin discovery: OK" if asin_ok else "asin discovery: FAIL")
    print("queue integration: OK" if queue_ok else "queue integration: FAIL")

    if not (search_url_ok and page_fetch_ok and product_card_ok and asin_ok and queue_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
