#!/usr/bin/env python3
"""
Step 199 smoke test: Workspace activity log layer.
Validates event creation, listing, summary stability, integration compatibility, empty resilience, non-blocking failure.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

SUMMARY_KEYS = {"workspace_id", "total", "by_event_type", "by_severity"}
EVENT_KEYS = {"id", "workspace_id", "event_type", "event_label", "actor_type", "actor_id", "source_module", "event_payload_json", "severity", "created_at"}


def main() -> None:
    from amazon_research.workspace_activity_log import (
        create_workspace_activity_event,
        list_workspace_activity_events,
        get_workspace_activity_summary,
    )

    creation_ok = True
    listing_ok = True
    summary_ok = True
    integration_ok = True
    empty_ok = True
    nonblocking_ok = True

    # --- Activity event creation: create returns id or None, never raises
    try:
        rid = create_workspace_activity_event(
            99999,
            "configuration_updated",
            event_label="Test",
            source_module="smoke_test",
            event_payload={"test": True},
        )
        if rid is not None and not isinstance(rid, int):
            creation_ok = False
    except Exception as e:
        creation_ok = False
        print(f"activity event creation error: {e}")

    # --- Activity listing: returns list with stable event shape
    try:
        events = list_workspace_activity_events(99999, limit=10)
        if not isinstance(events, list):
            listing_ok = False
        for ev in events:
            if not isinstance(ev, dict) or not EVENT_KEYS.issubset(ev.keys()):
                listing_ok = False
                break
    except Exception as e:
        listing_ok = False
        print(f"activity listing error: {e}")

    # --- Activity summary stability: get_workspace_activity_summary returns stable shape
    try:
        s = get_workspace_activity_summary(99999)
        if not isinstance(s, dict) or not SUMMARY_KEYS.issubset(s.keys()):
            summary_ok = False
        if not isinstance(s.get("by_severity"), dict):
            summary_ok = False
    except Exception as e:
        summary_ok = False
        print(f"activity summary stability error: {e}")

    # --- Integration logging compatibility: create with event types used by config/portfolio/alert/refresh
    try:
        for etype in ("configuration_updated", "portfolio_item_added", "alert_preferences_updated", "intelligence_refresh"):
            create_workspace_activity_event(99998, etype, source_module="smoke_test")
        integration_ok = True
    except Exception as e:
        integration_ok = False
        print(f"integration logging compatibility error: {e}")

    # --- Empty activity resilience: list/summary for workspace with no events (or no DB) don't crash
    try:
        empty_list = list_workspace_activity_events(99997, limit=5)
        empty_summary = get_workspace_activity_summary(99997)
        if not isinstance(empty_list, list):
            empty_ok = False
        if not isinstance(empty_summary, dict) or not SUMMARY_KEYS.issubset(empty_summary.keys()):
            empty_ok = False
    except Exception as e:
        empty_ok = False
        print(f"empty activity resilience error: {e}")

    # --- Non-blocking failure behavior: create with invalid/missing DB returns None, no exception
    try:
        # Pass workspace_id that may not exist or DB down - must not raise
        result = create_workspace_activity_event(None, "configuration_updated")
        if result is not None:
            nonblocking_ok = False
        result = create_workspace_activity_event(1, "configuration_updated", source_module="smoke_test")
        # With DB: may succeed or fail; without DB: fails with None. Either way no exception.
        if result is not None and not isinstance(result, int):
            nonblocking_ok = False
    except Exception as e:
        nonblocking_ok = False
        print(f"non-blocking failure behavior error: {e}")

    print("workspace activity log OK" if (creation_ok and listing_ok and summary_ok and integration_ok and empty_ok and nonblocking_ok) else "workspace activity log FAIL")
    print("activity event creation: OK" if creation_ok else "activity event creation: FAIL")
    print("activity listing: OK" if listing_ok else "activity listing: FAIL")
    print("activity summary stability: OK" if summary_ok else "activity summary stability: FAIL")
    print("integration logging compatibility: OK" if integration_ok else "integration logging compatibility: FAIL")
    print("empty activity resilience: OK" if empty_ok else "empty activity resilience: FAIL")
    print("non-blocking failure behavior: OK" if nonblocking_ok else "non-blocking failure behavior: FAIL")
    if not (creation_ok and listing_ok and summary_ok and integration_ok and empty_ok and nonblocking_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
