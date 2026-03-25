#!/usr/bin/env python3
"""Step 11: Data refresh bot base. Runs refresh on one test ASIN; stub returns no metrics."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection, upsert_asin
from amazon_research.bots import DataRefreshBot

TEST_ASIN = "STEP11SMOKE"

def main():
    init_db()
    upsert_asin(TEST_ASIN, title="Step 11 smoke")
    bot = DataRefreshBot()
    updated = bot.run(asin_list=[TEST_ASIN])
    # Stub returns {} so updated should be 0
    if updated != 0:
        print("FAIL: expected updated=0, got", updated)
        sys.exit(1)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM asins WHERE asin = %s", (TEST_ASIN,))
    conn.commit()
    cur.close()
    print("refresh bot base OK")
    print("updated:", updated)

if __name__ == "__main__":
    main()
