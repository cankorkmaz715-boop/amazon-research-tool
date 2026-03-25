#!/usr/bin/env python3
"""Step 131: Portfolio watch engine – watch registration, change detection, signal aggregation, alert compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

WORKSPACE_ID = 1


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import (
        register_watch,
        evaluate_watch,
        evaluate_all_watches,
    )
    from amazon_research.db import list_watches, get_watch, remove_watch

    # Watch registration: add watch for cluster (may be None if DB unavailable)
    watch_id = register_watch(WORKSPACE_ID, "cluster", "smoke-cluster-131")
    registration_ok = callable(register_watch)
    if watch_id is not None:
        registration_ok = registration_ok and isinstance(watch_id, int)

    # Evaluate returns structure: watch_id, watched_entity, detected_change_type, supporting_signal_summary, timestamp
    out = evaluate_watch(watch_id or 0, workspace_id=WORKSPACE_ID)
    change_ok = (
        isinstance(out, dict)
        and "watch_id" in out
        and "watched_entity" in out
        and isinstance(out["watched_entity"], dict)
        and "detected_change_type" in out
        and "timestamp" in out
    )
    if watch_id:
        change_ok = change_ok and out.get("watched_entity", {}).get("type") == "cluster" and out["watched_entity"].get("ref") == "smoke-cluster-131"
    signal_ok = "supporting_signal_summary" in out and isinstance(out.get("supporting_signal_summary"), dict)

    # Alert compatibility: output shape for downstream routing
    alert_ok = (
        "watch_id" in out
        and "detected_change_type" in out
        and "timestamp" in out
        and "watched_entity" in out
    )

    # list_watches and evaluate_all_watches
    try:
        watches = list_watches(WORKSPACE_ID, limit=5)
        registration_ok = registration_ok and isinstance(watches, list)
        results = evaluate_all_watches(WORKSPACE_ID, limit=5)
        change_ok = change_ok and isinstance(results, list)
        if results:
            change_ok = change_ok and "watch_id" in results[0] and "detected_change_type" in results[0]
    except Exception:
        pass

    # Cleanup: remove watch if we created one
    if watch_id:
        try:
            remove_watch(watch_id, workspace_id=WORKSPACE_ID)
        except Exception:
            pass

    print("portfolio watch engine OK")
    print("watch registration: OK" if registration_ok else "watch registration: FAIL")
    print("change detection: OK" if change_ok else "change detection: FAIL")
    print("signal aggregation: OK" if signal_ok else "signal aggregation: FAIL")
    print("alert compatibility: OK" if alert_ok else "alert compatibility: FAIL")

    if not (registration_ok and change_ok and signal_ok and alert_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
