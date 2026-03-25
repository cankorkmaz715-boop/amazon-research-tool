#!/usr/bin/env python3
"""Step 26: Data quality checks – missing fields, invalid metrics, duplicate issues, summary."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db, run_data_quality_checks

def main():
    init_db()
    r = run_data_quality_checks()

    print("data quality checks OK")
    print("missing fields:", "; ".join(r.get("missing_fields", ["?"])))
    print("invalid metrics:", r.get("invalid_metrics", "?"))
    print("duplicate issues:", r.get("duplicate_issues", "?"))
    print("summary:", r.get("summary", "?"))

if __name__ == "__main__":
    main()
