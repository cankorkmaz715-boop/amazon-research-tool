#!/usr/bin/env python3
"""Step 13: Scheduler readiness. Run discovery task once; verify no crash."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db
from amazon_research.scheduler import get_runner

def main():
    init_db()
    runner = get_runner()
    ran = runner.run_once("discovery")
    if "discovery" not in ran:
        print("FAIL: discovery did not run or failed")
        sys.exit(1)
    print("scheduler readiness OK")
    print("ran:", ran)

if __name__ == "__main__":
    main()
