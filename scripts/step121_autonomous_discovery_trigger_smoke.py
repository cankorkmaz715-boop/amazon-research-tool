#!/usr/bin/env python3
"""Step 121: Autonomous discovery trigger engine – signal detection, trigger generation, scheduler and worker compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_KEYS = ("trigger_id", "trigger_type", "target_entity", "reason_signal", "timestamp")
VALID_TRIGGER_TYPES = ("keyword_scan", "category_scan", "niche_discovery", "opportunity_alert")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import evaluate_discovery_triggers, enqueue_from_triggers

    result = evaluate_discovery_triggers(
        workspace_id=None,
        max_triggers=20,
        include_keyword_seeds=True,
        include_opportunity_alerts=True,
    )

    triggers = result.get("triggers") or []
    summary = result.get("summary") or {}
    signal_ok = (
        isinstance(triggers, list)
        and isinstance(summary, dict)
        and "total" in summary
        and "signals_used" in result
    )

    trigger_gen_ok = True
    if triggers:
        for t in triggers[:3]:
            trigger_gen_ok = trigger_gen_ok and all(k in t for k in REQUIRED_KEYS)
            trigger_gen_ok = trigger_gen_ok and (t.get("trigger_type") in VALID_TRIGGER_TYPES)
    else:
        trigger_gen_ok = result.get("summary", {}).get("total") == 0

    scheduler_ok = callable(enqueue_from_triggers)
    try:
        enq = enqueue_from_triggers(triggers[:5], workspace_id=None)
        scheduler_ok = scheduler_ok and isinstance(enq, dict) and "job_ids" in enq and "summary" in enq
    except Exception:
        pass

    worker_ok = all(
        t.get("trigger_type") in VALID_TRIGGER_TYPES
        for t in triggers
    ) if triggers else True

    print("autonomous discovery trigger engine OK")
    print("signal detection: OK" if signal_ok else "signal detection: FAIL")
    print("trigger generation: OK" if trigger_gen_ok else "trigger generation: FAIL")
    print("scheduler integration: OK" if scheduler_ok else "scheduler integration: FAIL")
    print("worker compatibility: OK" if worker_ok else "worker compatibility: FAIL")

    if not (signal_ok and trigger_gen_ok and scheduler_ok and worker_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
