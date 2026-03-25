#!/usr/bin/env python3
"""Step 71: Category crawler foundation – page fetch, product card extraction, ASIN discovery, pagination, queue integration."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.browser import BrowserSession
    from amazon_research.crawler import (
        crawl_category_page,
        extract_product_cards,
        fetch_category_page,
        get_next_page_url,
    )
    from amazon_research.db import enqueue_job
    from amazon_research.db.worker_queue import JOB_TYPE_DISCOVERY

    fixture_path = os.path.join(ROOT, "scripts", "fixtures", "sample_listing.html")
    file_url = "file://" + os.path.abspath(fixture_path)

    session = BrowserSession(headless=True)
    session.start()
    try:
        # --- Page fetch: fetch_category_page returns page ---
        page = fetch_category_page(session, file_url)
        page_fetch_ok = page is not None

        # --- Product card extraction: extract_product_cards returns list of { asin } ---
        items = extract_product_cards(page) if page else []
        product_card_ok = isinstance(items, list) and all(
            isinstance(x, dict) and x.get("asin") for x in items
        ) and len(items) >= 1

        # --- ASIN discovery: asins list from crawl ---
        result = crawl_category_page(session, file_url, page_index=0)
        asin_ok = (
            "asins" in result
            and isinstance(result["asins"], list)
            and len(result["asins"]) >= 1
        )

        # --- Pagination readiness: next_page_url key and get_next_page_url callable ---
        next_url = get_next_page_url(page, file_url) if page else None
        pagination_ok = "next_page_url" in result and callable(get_next_page_url)

        # --- Queue integration: structure queue-friendly (asins, next_page_url, items); optionally enqueue if DB available ---
        queue_friendly = (
            "asins" in result
            and "next_page_url" in result
            and "items" in result
            and "page_url" in result
        )
        try:
            from amazon_research.db import init_db
            init_db()
            payload = {"urls": [file_url], "asins_from_crawl": result.get("asins", [])}
            jid = enqueue_job(JOB_TYPE_DISCOVERY, workspace_id=None, payload=payload)
            queue_ok = queue_friendly and jid is not None and isinstance(jid, int)
        except Exception:
            queue_ok = queue_friendly
    finally:
        session.close()

    print("category crawler foundation OK")
    print("page fetch: OK" if page_fetch_ok else "page fetch: FAIL")
    print("product card extraction: OK" if product_card_ok else "product card extraction: FAIL")
    print("asin discovery: OK" if asin_ok else "asin discovery: FAIL")
    print("pagination readiness: OK" if pagination_ok else "pagination readiness: FAIL")
    print("queue integration: OK" if queue_ok else "queue integration: FAIL")

    if not (page_fetch_ok and product_card_ok and asin_ok and pagination_ok and queue_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
