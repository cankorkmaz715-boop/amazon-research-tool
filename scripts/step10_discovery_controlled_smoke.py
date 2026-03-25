#!/usr/bin/env python3
"""Step 10: Discovery bot on a small controlled flow. Uses local fixture HTML; no live Amazon."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection
from amazon_research.bots import AsinDiscoveryBot

FIXTURE_HTML = os.path.join(ROOT, "scripts", "fixtures", "sample_listing.html")
EXPECTED_ASINS = {"B00STEP101", "B00STEP102", "B00STEP103"}

def main():
    if not os.path.isfile(FIXTURE_HTML):
        print("FAIL: fixture not found", FIXTURE_HTML)
        sys.exit(1)
    file_url = "file://" + FIXTURE_HTML

    init_db()
    bot = AsinDiscoveryBot()
    result = bot.run(urls=[file_url])
    if not isinstance(result, list):
        print("FAIL: run() did not return a list")
        sys.exit(1)
    found = set(result)
    if found != EXPECTED_ASINS:
        print("FAIL: expected ASINs", EXPECTED_ASINS, "got", found)
        sys.exit(1)
    # Clean up test ASINs
    conn = get_connection()
    cur = conn.cursor()
    for asin in EXPECTED_ASINS:
        cur.execute("DELETE FROM asins WHERE asin = %s", (asin,))
    conn.commit()
    cur.close()
    print("discovery controlled flow OK")
    print("discovered:", len(result), "ASINs:", sorted(result))

if __name__ == "__main__":
    main()
