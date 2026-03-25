#!/usr/bin/env python3
"""Step 125: Opportunity lifecycle tracker – state detection, score evolution, memory and dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

VALID_STATES = ("new", "rising", "stable", "weakening", "fading")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_opportunity_lifecycle, list_opportunities_with_lifecycle

    # With no memory record: should return stable/default with rationale "no memory record"
    out_none = get_opportunity_lifecycle("nonexistent-ref-125", memory_record=None)
    state_ok = (
        out_none.get("opportunity_id") == "nonexistent-ref-125"
        and out_none.get("lifecycle_state") in VALID_STATES
        and "rationale" in out_none
        and "supporting_signals" in out_none
    )

    # With synthetic memory record: score evolution and state
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    recent = now - timedelta(days=2)
    mem_rising = {
        "opportunity_ref": "smoke-rising-125",
        "first_seen_at": recent,
        "last_seen_at": now,
        "status": "strengthening",
        "score_history": [{"at": (recent - timedelta(days=1)).isoformat(), "score": 50}, {"at": now.isoformat(), "score": 70}],
        "latest_opportunity_score": 70,
    }
    life_rising = get_opportunity_lifecycle("smoke-rising-125", memory_record=mem_rising)
    score_evolution_ok = (
        life_rising.get("lifecycle_state") == "rising"
        and "score_trend" in life_rising.get("supporting_signals", {})
    )

    mem_stable = {
        "opportunity_ref": "smoke-stable-125",
        "first_seen_at": recent,
        "last_seen_at": now,
        "status": "recurring",
        "score_history": [{"at": now.isoformat(), "score": 60}],
        "latest_opportunity_score": 60,
    }
    life_stable = get_opportunity_lifecycle("smoke-stable-125", memory_record=mem_stable)
    memory_ok = (
        life_stable.get("lifecycle_state") in ("stable", "new")
        and isinstance(life_stable.get("supporting_signals"), dict)
        and "memory_status" in life_stable.get("supporting_signals", {})
    )

    listing = list_opportunities_with_lifecycle(limit=5)
    dashboard_ok = isinstance(listing, list)
    if listing:
        first = listing[0]
        dashboard_ok = dashboard_ok and "lifecycle" in first
        lc = first.get("lifecycle") or {}
        dashboard_ok = dashboard_ok and "lifecycle_state" in lc and "rationale" in lc

    print("opportunity lifecycle tracker OK")
    print("lifecycle state detection: OK" if state_ok else "lifecycle state detection: FAIL")
    print("score evolution handling: OK" if score_evolution_ok else "score evolution handling: FAIL")
    print("memory compatibility: OK" if memory_ok else "memory compatibility: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (state_ok and score_evolution_ok and memory_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
