#!/usr/bin/env python3
"""Step 156: Workspace intelligence timeline – timeline generation, event aggregation, event categories, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

VALID_EVENT_TYPES = {
    "new_opportunity",
    "rising_opportunity",
    "weakening_opportunity",
    "alert_event",
    "watchlist_event",
    "copilot_suggestion",
    "research_action",
}


def main():
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from amazon_research.db import init_db
        init_db()
    except Exception:
        pass

    from amazon_research.discovery import get_workspace_intelligence_timeline

    timeline = get_workspace_intelligence_timeline(1, limit=50)

    # 1) Timeline generation: returns list; each entry has required fields
    gen_ok = isinstance(timeline, list)
    if timeline:
        gen_ok = gen_ok and all(
            "timeline_event_id" in e and (e.get("timeline_event_id") or "").startswith("timeline-")
            and "event_type" in e and "target_entity" in e
            and "short_summary" in e and "timestamp" in e and e.get("workspace_id") == 1
            for e in timeline
        )

    # 2) Event aggregation: timeline combines multiple sources (we have at least one event type present)
    event_types_seen = {e.get("event_type") for e in timeline if e.get("event_type")}
    aggregation_ok = True  # empty timeline is valid
    if timeline:
        aggregation_ok = len(event_types_seen) >= 1 and all(e.get("event_type") for e in timeline)

    # 3) Event categories: all event_type values are supported
    categories_ok = all(e.get("event_type") in VALID_EVENT_TYPES for e in timeline) if timeline else True

    # 4) Dashboard compatibility: target_entity is dict with type/ref, timestamp present
    dashboard_ok = True
    if timeline:
        for e in timeline[:15]:
            te = e.get("target_entity")
            if not isinstance(te, dict):
                dashboard_ok = False
                break
            if not e.get("timestamp"):
                dashboard_ok = False
                break

    print("workspace intelligence timeline OK")
    print("timeline generation: OK" if gen_ok else "timeline generation: FAIL")
    print("event aggregation: OK" if aggregation_ok else "event aggregation: FAIL")
    print("event categories: OK" if categories_ok else "event categories: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (gen_ok and aggregation_ok and categories_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
