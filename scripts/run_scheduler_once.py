#!/usr/bin/env python3
"""
Run the scheduler pipeline once (discovery → refresh → scoring).
Use this as the cron/systemd entrypoint for recurring execution.
From repo root: python scripts/run_scheduler_once.py
Or: PYTHONPATH=src python -m amazon_research.run_scheduler_once
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.logging_config import setup_logging, get_logger
    setup_logging()
    log = get_logger("run_scheduler_once")
    from amazon_research.db import init_db
    from amazon_research.scheduler import get_runner
    init_db()
    runner = get_runner()
    result = runner.run_pipeline()
    if result.get("ok"):
        log.info("pipeline completed", extra={"stages": result.get("stages_completed", [])})
    else:
        log.warning("pipeline stopped", extra={"stopped_at": result.get("stopped_at"), "error": result.get("error")})
    sys.exit(0 if result.get("ok") else 1)

if __name__ == "__main__":
    main()
