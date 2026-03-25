#!/usr/bin/env python3
"""Step 18: Multi-Page Discovery v2 – up to 2–3 URLs, conservative nav, dedupe across pages. Set DISCOVERY_TEST_URLS (comma-separated)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

raw = os.environ.get("DISCOVERY_TEST_URLS", "").strip()
if not raw:
    print("Set DISCOVERY_TEST_URLS in .env to 2–3 comma-separated Amazon listing URLs (e.g. search page 1, page 2).")
    sys.exit(1)
urls = [u.strip() for u in raw.split(",") if u.strip()]
if not urls:
    print("DISCOVERY_TEST_URLS is empty after split.")
    sys.exit(1)

from amazon_research.db import init_db
from amazon_research.bots import AsinDiscoveryBot

def main():
    init_db()
    bot = AsinDiscoveryBot()
    result = bot.run(urls=urls)
    print("multi-page discovery v2 OK")
    print("pages visited:", min(len(urls), 3), "(cap 3)")
    print("discovered (deduped):", len(result), "ASINs")
    if result:
        print("first 5:", result[:5])

if __name__ == "__main__":
    main()
