#!/usr/bin/env python3
"""Step 15: Real Discovery v1 – one Amazon listing URL, extract ASINs, persist. Set DISCOVERY_TEST_URL in .env."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

url = os.environ.get("DISCOVERY_TEST_URL", "").strip()
if not url or "amazon" not in url.lower():
    print("Set DISCOVERY_TEST_URL in .env to one Amazon listing/search URL (e.g. a search results page).")
    sys.exit(1)

from amazon_research.db import init_db
from amazon_research.bots import AsinDiscoveryBot

def main():
    init_db()
    bot = AsinDiscoveryBot()
    result = bot.run(urls=[url])
    print("real discovery v1 OK")
    print("discovered:", len(result), "ASINs")
    if result:
        print("first 5:", result[:5])

if __name__ == "__main__":
    main()
