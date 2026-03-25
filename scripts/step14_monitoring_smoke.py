#!/usr/bin/env python3
"""Step 14: Monitoring hooks readiness. Health check (with DB) and capture_exception."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db
from amazon_research.monitoring import health_check, capture_exception

def main():
    init_db()
    health = health_check()
    if health.get("status") != "ok" or health.get("db") != "ok":
        print("FAIL: health_check", health)
        sys.exit(1)
    capture_exception(ValueError("step14 smoke test"), context={"step": 14})
    print("monitoring hooks OK")
    print("health:", health)

if __name__ == "__main__":
    main()
