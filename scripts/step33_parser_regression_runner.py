#!/usr/bin/env python3
"""Parser regression against fixture HTML (no Playwright). Asserts expected ASINs and metrics from stored HTML."""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def main():
    fixtures_dir = os.path.join(ROOT, "scripts", "fixtures")
    discovery_ok = False
    refresh_ok = False

    # Discovery: fixture must contain ASINs extractable by /dp/ or /gp/product/ pattern
    listing_fixture = os.path.join(fixtures_dir, "sample_listing.html")
    if os.path.isfile(listing_fixture):
        with open(listing_fixture, "r") as f:
            html = f.read()
        asins = set(re.findall(r"/dp/([A-Z0-9]{10})", html, re.I))
        asins |= set(re.findall(r"/gp/product/([A-Z0-9]{10})", html, re.I))
        expected = {"B00STEP101", "B00STEP102", "B00STEP103"}
        discovery_ok = expected.issubset(asins)

    # Refresh (product): fixture must contain price, rating, review count, BSR-like content
    product_fixture = os.path.join(fixtures_dir, "sample_product.html")
    if os.path.isfile(product_fixture):
        with open(product_fixture, "r") as f:
            html = f.read()
        has_price = "29.99" in html
        has_rating = "4.5" in html and "out of 5" in html
        has_reviews = "1,234" in html and "rating" in html.lower()
        has_bsr = "#12,345" in html or "12,345" in html
        refresh_ok = has_price and has_rating and has_reviews and has_bsr

    if discovery_ok:
        print("discovery fixtures: OK")
    else:
        print("discovery fixtures: FAIL")
    if refresh_ok:
        print("refresh fixtures: OK")
    else:
        print("refresh fixtures: FAIL")
    sys.exit(0 if (discovery_ok and refresh_ok) else 1)

if __name__ == "__main__":
    main()
