#!/usr/bin/env python3
"""Step 7: Verify initial schema tables exist. Run run_schema.py first if needed."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, get_connection

EXPECTED_TABLES = [
    "asins", "product_metrics", "price_history", "review_history",
    "category_scans", "scoring_results", "bot_runs", "error_logs",
]

def main():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = ANY(%s)",
        (EXPECTED_TABLES,),
    )
    found = {row[0] for row in cur.fetchall()}
    cur.close()
    missing = set(EXPECTED_TABLES) - found
    if missing:
        print("Missing tables:", missing)
        sys.exit(1)
    print("schema OK: all 8 tables present")
    print("tables:", ", ".join(sorted(found)))

if __name__ == "__main__":
    main()
