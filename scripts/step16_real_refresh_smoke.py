#!/usr/bin/env python3
"""Step 16: Real Refresh v1 – load one ASIN from DB, open product page, extract metrics, persist. Prints result."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection, get_asin_id

def main():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT asin FROM asins ORDER BY id LIMIT 1")
    row = cur.fetchone()
    cur.close()
    if not row:
        print("No ASIN in DB. Run discovery first (e.g. step15) to add at least one ASIN.")
        sys.exit(1)
    asin = row[0]

    from amazon_research.bots import DataRefreshBot
    bot = DataRefreshBot()
    updated = bot.run(asin_list=[asin])
    if updated == 0:
        print("refresh v1 OK (no metrics extracted – selectors may need tuning for this page)")
    else:
        print("refresh v1 OK")

    asin_id = get_asin_id(asin)
    cur = conn.cursor()
    cur.execute(
        "SELECT price, currency, bsr, rating, review_count FROM product_metrics WHERE asin_id = %s",
        (asin_id,),
    )
    m = cur.fetchone()
    cur.close()
    print("ASIN:", asin)
    if m:
        price, currency, bsr, rating, review_count = m
        print("price:", f"{price} {currency}" if price is not None else "—")
        print("rating:", rating if rating is not None else "—")
        print("reviews:", review_count if review_count is not None else "—")
        print("BSR:", (bsr[:200] + "…" if bsr and len(bsr) > 200 else bsr) if bsr else "—")
    else:
        print("price: —")
        print("rating: —")
        print("reviews: —")
        print("BSR: —")

if __name__ == "__main__":
    main()
