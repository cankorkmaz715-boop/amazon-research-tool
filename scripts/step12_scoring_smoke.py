#!/usr/bin/env python3
"""Step 12: Scoring engine base. Score one test ASIN, verify placeholder scores persisted."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection, upsert_asin
from amazon_research.bots import ScoringEngine

TEST_ASIN = "STEP12SMOKE"

def main():
    init_db()
    upsert_asin(TEST_ASIN, title="Step 12 smoke")
    engine = ScoringEngine()
    results = engine.run(asin_list=[TEST_ASIN])
    if len(results) != 1:
        print("FAIL: expected 1 result, got", len(results))
        sys.exit(1)
    r = results[0]
    if r.get("asin") != TEST_ASIN or r.get("opportunity_score") != 0.5:
        print("FAIL: unexpected result", r)
        sys.exit(1)
    # Clean up (cascade deletes scoring_results)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM asins WHERE asin = %s", (TEST_ASIN,))
    conn.commit()
    cur.close()
    print("scoring engine base OK")
    print("scored:", r["asin"], "opportunity_score:", r["opportunity_score"])

if __name__ == "__main__":
    main()
