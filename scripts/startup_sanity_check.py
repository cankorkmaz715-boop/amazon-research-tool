#!/usr/bin/env python3
"""
Step 229: Startup sanity check – validate required env and optionally DB connect.
Run before or after deploy to confirm the app is launchable. Exit 0 if OK, 1 on failure.
Usage: python scripts/startup_sanity_check.py [--db]   # --db = also check DB connection
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

# Load .env before importing app code
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def main() -> int:
    do_db = "--db" in sys.argv
    try:
        from amazon_research.deployment_hardening import run_startup_checks
        ok, errors = run_startup_checks(skip_db_connect=not do_db)
        if ok:
            print("Startup sanity check OK.")
            return 0
        for msg in errors:
            print(msg, file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Startup sanity check failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
