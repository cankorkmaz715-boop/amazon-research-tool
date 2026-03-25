"""
Run scheduler pipeline once. Entrypoint for cron/systemd.
Invoke: python -m amazon_research.run_scheduler_once (from repo root with PYTHONPATH=src or from project root).
"""
import os
import sys

# Allow running as module from repo root
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if os.path.basename(_ROOT) == "src":
    _ROOT = os.path.dirname(_ROOT)
os.chdir(_ROOT)
if "src" not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "src"))


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
