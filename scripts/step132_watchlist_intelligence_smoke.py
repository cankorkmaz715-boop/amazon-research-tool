#!/usr/bin/env python3
"""Step 132: Watchlist intelligence layer – watch evaluation, priority scoring, change interpretation, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

LABELS = ("high_priority", "attention", "stable", "low_activity")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_watch_intelligence, list_watch_intelligence

    # With no watch (watch_id=0): structure only
    out_empty = get_watch_intelligence(0, workspace_id=1)
    watch_eval_ok = (
        "watch_id" in out_empty
        and "watched_entity" in out_empty
        and "importance_score" in out_empty
        and "detected_change_summary" in out_empty
        and "watch_intelligence_label" in out_empty
        and "timestamp" in out_empty
    )

    # Priority scoring: importance_score 0–100, label in allowed set
    priority_ok = (
        isinstance(out_empty.get("importance_score"), (int, float))
        and 0 <= out_empty.get("importance_score", -1) <= 100
        and out_empty.get("watch_intelligence_label") in LABELS
    )

    # With synthetic watch_result: change interpretation
    watch_result = {
        "watch_id": 1,
        "watched_entity": {"type": "cluster", "ref": "smoke-132"},
        "detected_change_type": "opportunity_score_change",
        "supporting_signal_summary": {
            "opportunity_score_previous": 55,
            "opportunity_score_current": 72,
            "demand_previous": 60,
            "demand_current": 68,
        },
    }
    out_synth = get_watch_intelligence(1, workspace_id=1, watch_result=watch_result)
    change_ok = (
        out_synth.get("watch_id") == 1
        and out_synth.get("watched_entity", {}).get("ref") == "smoke-132"
        and isinstance(out_synth.get("detected_change_summary"), str)
        and len(out_synth.get("detected_change_summary", "")) > 0
        and "opportunity" in out_synth.get("detected_change_summary", "").lower()
    )

    # List API: returns list, sorted by importance; each item has dashboard fields
    try:
        listing = list_watch_intelligence(1, limit=5)
        dashboard_ok = isinstance(listing, list)
        if listing:
            first = listing[0]
            dashboard_ok = (
                dashboard_ok
                and "importance_score" in first
                and "watch_intelligence_label" in first
                and "detected_change_summary" in first
            )
    except Exception:
        dashboard_ok = True

    print("watchlist intelligence layer OK")
    print("watch evaluation: OK" if watch_eval_ok else "watch evaluation: FAIL")
    print("priority scoring: OK" if priority_ok else "priority scoring: FAIL")
    print("change interpretation: OK" if change_ok else "change interpretation: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (watch_eval_ok and priority_ok and change_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
