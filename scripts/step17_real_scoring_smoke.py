#!/usr/bin/env python3
"""Step 17: Real Scoring v1 – score ASINs from stored product_metrics only, persist to scoring_results. Prints result."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection

def main():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT asin FROM asins ORDER BY id LIMIT 5")
    rows = cur.fetchall()
    cur.close()
    if not rows:
        print("No ASINs in DB. Run discovery (e.g. step15) first.")
        sys.exit(1)
    asin_list = [r[0] for r in rows]

    from amazon_research.bots import ScoringEngine
    engine = ScoringEngine()
    results = engine.run(asin_list=asin_list)
    if not results:
        print("No ASINs scored (none had asin_id in DB?).")
        sys.exit(1)

    print("real scoring v1 OK")
    print("scored:", len(results), "ASIN(s)")
    for r in results:
        print("  ASIN:", r["asin"], "| demand:", r["demand_score"], "| competition:", r["competition_score"], "| opportunity:", r["opportunity_score"])

if __name__ == "__main__":
    main()
