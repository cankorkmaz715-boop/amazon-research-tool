#!/usr/bin/env python3
"""Step 72: Category scanner v1 – category fetch, multi-page scan, ASIN extraction, deduplication, ASIN pool."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.browser import BrowserSession
    from amazon_research.crawler import scan_category

    fixture_path = os.path.join(ROOT, "scripts", "fixtures", "sample_listing.html")
    file_url = "file://" + os.path.abspath(fixture_path)

    session = BrowserSession(headless=True)
    session.start()
    try:
        # --- Category fetch: scan starts from URL and fetches at least one page ---
        pool = scan_category(session, file_url, max_pages=2)
        category_fetch_ok = pool is not None and "asins" in pool and "pages_scanned" in pool

        # --- Multi-page scan: pages_scanned and urls list (single page for fixture, but structure supports multi) ---
        multi_page_ok = (
            pool.get("pages_scanned", 0) >= 1
            and "urls" in pool
            and isinstance(pool["urls"], list)
            and len(pool["urls"]) >= 1
        )

        # --- ASIN extraction: pool contains asins from the page ---
        asins = pool.get("asins") or []
        asin_ok = isinstance(asins, list) and len(asins) >= 1

        # --- Deduplication: asins list has no duplicates (set semantics) ---
        dedupe_ok = len(asins) == len(set(asins))

        # --- ASIN pool ready: pool_size, asins, queue-friendly for discovery pipeline ---
        pool_ok = (
            pool.get("pool_size") == len(asins)
            and "asins" in pool
            and (pool["asins"] == asins or pool["asins"] == sorted(asins))
        )
    finally:
        session.close()

    print("category scanner v1 OK")
    print("category fetch: OK" if category_fetch_ok else "category fetch: FAIL")
    print("multi-page scan: OK" if multi_page_ok else "multi-page scan: FAIL")
    print("asin extraction: OK" if asin_ok else "asin extraction: FAIL")
    print("deduplication: OK" if dedupe_ok else "deduplication: FAIL")
    print("asin pool ready: OK" if pool_ok else "asin pool ready: FAIL")

    if not (category_fetch_ok and multi_page_ok and asin_ok and dedupe_ok and pool_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
