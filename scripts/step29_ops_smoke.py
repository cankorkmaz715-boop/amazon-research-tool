#!/usr/bin/env python3
"""Step 29: Ops readiness – scheduler entrypoint, cron/systemd config examples, enable/disable docs."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    # 1) Scheduler entrypoint: run_scheduler_once completes (or exits 1 on stage failure)
    ok_entrypoint = False
    try:
        from dotenv import load_dotenv
        load_dotenv()
        from amazon_research.db import init_db
        from amazon_research.scheduler import get_runner
        init_db()
        runner = get_runner()
        result = runner.run_pipeline()
        ok_entrypoint = "stages_completed" in result and "ok" in result
    except Exception as e:
        ok_entrypoint = False

    # 2) Cron/systemd config files exist
    cron_ex = os.path.join(ROOT, "config", "cron.example")
    svc_ex = os.path.join(ROOT, "config", "amazon-research.service.example")
    timer_ex = os.path.join(ROOT, "config", "amazon-research.timer.example")
    ok_cron = os.path.isfile(cron_ex)
    ok_svc = os.path.isfile(svc_ex)
    ok_timer = os.path.isfile(timer_ex)
    ok_config = ok_cron and ok_svc and ok_timer

    # 3) Enable/disable instructions exist
    ops_doc = os.path.join(ROOT, "OPS-RECURRING.md")
    ok_docs = os.path.isfile(ops_doc)
    if ok_docs:
        with open(ops_doc, "r") as f:
            text = f.read()
        ok_docs = "Enable" in text and "Disable" in text and "run_scheduler_once" in text

    # 4) Script entrypoint exists and is runnable
    script_path = os.path.join(ROOT, "scripts", "run_scheduler_once.py")
    ok_script = os.path.isfile(script_path)

    print("ops readiness OK")
    print("scheduler entrypoint: OK" if (ok_entrypoint and ok_script) else "scheduler entrypoint: FAIL")
    print("cron/systemd config: OK" if ok_config else "cron/systemd config: FAIL")
    print("enable/disable instructions: OK" if ok_docs else "enable/disable instructions: FAIL")

    if not (ok_entrypoint and ok_script and ok_config and ok_docs):
        sys.exit(1)

if __name__ == "__main__":
    main()
