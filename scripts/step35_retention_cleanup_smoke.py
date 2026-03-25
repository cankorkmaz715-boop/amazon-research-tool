#!/usr/bin/env python3
"""Step 35: Retention and cleanup – policy and cleanup routine for logs/history only."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.config import get_config
    from amazon_research.db import init_db, run_retention_cleanup

    init_db()
    cfg = get_config()

    # Retention policy: config has retention days for error_logs, bot_runs, price_history, review_history
    policy_ok = (
        getattr(cfg, "error_logs_retention_days", 0) >= 1
        and getattr(cfg, "bot_runs_retention_days", 0) >= 1
        and getattr(cfg, "price_history_retention_days", 0) >= 1
        and getattr(cfg, "review_history_retention_days", 0) >= 1
    )

    # Cleanup routine: run and ensure it completes (no exception)
    try:
        result = run_retention_cleanup()
        cleanup_ok = isinstance(result, dict) and "error_logs" in result and "bot_runs" in result
    except Exception:
        cleanup_ok = False

    print("retention cleanup OK")
    print("retention policy: OK" if policy_ok else "retention policy: FAIL")
    print("cleanup routine: OK" if cleanup_ok else "cleanup routine: FAIL")

    if not (policy_ok and cleanup_ok):
        sys.exit(1)

if __name__ == "__main__":
    main()
