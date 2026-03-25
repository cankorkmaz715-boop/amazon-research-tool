#!/usr/bin/env python3
"""Step 19: Refresh Batch v2 – load small ASIN batch from DB, refresh sequentially, persist, print metrics."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection, get_asin_id
from amazon_research.bots import DataRefreshBot

def main():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT asin FROM asins ORDER BY id LIMIT 5")
    rows = cur.fetchall()
    cur.close()
    if not rows:
        print("No ASINs in DB. Run discovery (e.g. step15/18) first.")
        sys.exit(1)
    asin_list = [r[0] for r in rows]

    bot = DataRefreshBot()
    updated = bot.run(asin_list=asin_list)
    print("refresh batch v2 OK")
    print("batch size:", len(asin_list), "| updated:", updated)

    cur = conn.cursor()
    for asin in asin_list:
        asin_id = get_asin_id(asin)
        if not asin_id:
            print("  ASIN:", asin, "| (not in DB)")
            continue
        cur.execute(
            "SELECT price, currency, bsr, rating, review_count FROM product_metrics WHERE asin_id = %s",
            (asin_id,),
        )
        m = cur.fetchone()
        if m:
            price, currency, bsr, rating, review_count = m
            bsr_short = (bsr[:60] + "…") if bsr and len(bsr) > 60 else (bsr or "—")
            print("  ASIN:", asin, "| price:", price, currency or "", "| rating:", rating, "| reviews:", review_count, "| BSR:", bsr_short)
        else:
            print("  ASIN:", asin, "| (no metrics yet)")
    cur.close()

if __name__ == "__main__":
    main()
