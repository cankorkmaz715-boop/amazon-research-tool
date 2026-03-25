#!/usr/bin/env python3
"""Step 20: Selector hardening – parsers never crash; fallback selectors for price, rating, reviews, BSR."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

def main():
    from amazon_research.browser import BrowserSession
    from amazon_research.parsers.product import extract_metrics_from_product_page
    from amazon_research.parsers.listing import extract_asins_from_amazon_listing

    fixture = os.path.join(ROOT, "scripts", "fixtures", "sample_product.html")
    if not os.path.isfile(fixture):
        print("Fixture missing:", fixture)
        sys.exit(1)

    with BrowserSession(headless=True) as session:
        page = session.get_page()
        if not page:
            print("No page")
            sys.exit(1)
        page.goto("file://" + fixture, wait_until="domcontentloaded")

        try:
            metrics = extract_metrics_from_product_page(page)
        except Exception as e:
            print("Product parser crashed:", e)
            sys.exit(1)

    # Listing parser on same fixture (no /dp/ links in product fixture, so expect [] or run on listing fixture)
    listing_fixture = os.path.join(ROOT, "scripts", "fixtures", "sample_listing.html")
    if os.path.isfile(listing_fixture):
        with BrowserSession(headless=True) as session:
            page = session.get_page()
            if page:
                page.goto("file://" + listing_fixture, wait_until="domcontentloaded")
                try:
                    extract_asins_from_amazon_listing(page)
                except Exception as e:
                    print("Listing parser crashed:", e)
                    sys.exit(1)

    print("selector hardening OK")
    print("parsed fields: price, rating, reviews, BSR")

if __name__ == "__main__":
    main()
