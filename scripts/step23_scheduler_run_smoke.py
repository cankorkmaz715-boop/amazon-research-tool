#!/usr/bin/env python3
"""Step 23: Scheduler Execution v1 – run discovery → refresh → scoring in one controlled sequence."""
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
    result = runner.run_pipeline()

    print("scheduler execution v1 OK")
    for stage in ["discovery", "refresh", "scoring"]:
        if stage in result.get("stages_completed", []):
            print(f"{stage} stage OK")
    if result.get("ok"):
        print("pipeline completed")
    else:
        print("pipeline stopped at:", result.get("stopped_at", "?"), "-", result.get("error", ""))
        sys.exit(1)

if __name__ == "__main__":
    main()
