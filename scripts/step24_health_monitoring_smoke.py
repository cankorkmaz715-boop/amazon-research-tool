#!/usr/bin/env python3
"""Step 24: Health / Monitoring upgrade – db, browser, proxy, scheduler readiness."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db
from amazon_research.monitoring import health_check

def main():
    init_db()
    h = health_check()

    print("health monitoring upgrade OK")
    print("db:", h.get("db", "?"))
    print("browser:", h.get("browser", "?"))
    proxy_val = h.get("proxy", "?")
    print("proxy:", "ok" if proxy_val in ("enabled", "disabled") else proxy_val)
    print("scheduler:", h.get("scheduler", "?"))

    if h.get("db") != "ok" or h.get("browser") != "ok" or h.get("scheduler") != "ok":
        sys.exit(1)
    if proxy_val not in ("enabled", "disabled"):
        sys.exit(1)

if __name__ == "__main__":
    main()
