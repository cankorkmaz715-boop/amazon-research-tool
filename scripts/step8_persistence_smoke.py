#!/usr/bin/env python3
"""Step 8: Persistence layer. Upsert ASIN, metrics, append history; then remove test row."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import (
    init_db,
    get_connection,
    upsert_asin,
    get_asin_id,
    upsert_product_metrics,
    append_price_history,
    append_review_history,
)

TEST_ASIN = "STEP8SMOKE"

def main():
    init_db()
    # Upsert ASIN
    asin_id = upsert_asin(TEST_ASIN, title="Step 8 smoke test", category="Test")
    if asin_id is None:
        print("FAIL: upsert_asin returned None")
        sys.exit(1)
    # Get by asin
    found_id = get_asin_id(TEST_ASIN)
    if found_id != asin_id:
        print("FAIL: get_asin_id", found_id, "!=", asin_id)
        sys.exit(1)
    # Metrics and history
    upsert_product_metrics(asin_id, price=12.99, currency="USD", rating=4.5, review_count=100)
    append_price_history(asin_id, 12.99, "USD")
    append_review_history(asin_id, review_count=100, rating=4.5)
    # Remove test data (cascade deletes metrics/history)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM asins WHERE asin = %s", (TEST_ASIN,))
    conn.commit()
    cur.close()
    print("persistence OK")

if __name__ == "__main__":
    main()
