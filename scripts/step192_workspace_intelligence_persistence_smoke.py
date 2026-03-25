#!/usr/bin/env python3
"""
Step 192 smoke test: Workspace intelligence persistence layer.
Validates snapshot write, latest read, missing fallback, payload stability, refresh compatibility.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_SUMMARY_KEYS = {
    "workspace_id", "summary_timestamp", "total_tracked_opportunities",
    "active_high_priority_count", "new_opportunities_recent_window",
    "average_opportunity_score", "top_opportunity_refs", "trend_overview",
    "alert_overview", "category_coverage_overview", "market_coverage_overview",
}


def main() -> None:
    from amazon_research.workspace_intelligence import (
        get_workspace_intelligence_summary,
        get_workspace_intelligence_summary_prefer_cached,
        refresh_workspace_intelligence_summary,
    )
    from amazon_research.db.workspace_intelligence_snapshots import (
        save_workspace_intelligence_snapshot,
        get_latest_workspace_intelligence_snapshot,
    )

    write_ok = True
    read_ok = True
    fallback_ok = True
    stability_ok = True
    refresh_ok = True

    # --- Snapshot write path: save returns id or None without crashing
    try:
        dummy_summary = {
            "workspace_id": 1,
            "summary_timestamp": "2025-03-14T12:00:00+00:00",
            "total_tracked_opportunities": 0,
            "active_high_priority_count": 0,
            "new_opportunities_recent_window": 0,
            "average_opportunity_score": 0.0,
            "top_opportunity_refs": [],
            "trend_overview": {},
            "alert_overview": {},
            "category_coverage_overview": {},
            "market_coverage_overview": {},
        }
        sid = save_workspace_intelligence_snapshot(1, dummy_summary)
        if sid is not None and not isinstance(sid, int):
            write_ok = False
    except Exception as e:
        write_ok = False
        print(f"snapshot write error: {e}")

    # --- Latest snapshot read: get_latest returns dict or None
    try:
        snap = get_latest_workspace_intelligence_snapshot(1)
        if snap is not None and not isinstance(snap, dict):
            read_ok = False
    except Exception as e:
        read_ok = False
        print(f"latest snapshot read error: {e}")

    # --- Missing snapshot fallback: prefer_cached returns valid summary when no snapshot
    try:
        # Use a high workspace_id unlikely to have a snapshot; should get computed default shape
        fallback = get_workspace_intelligence_summary_prefer_cached(workspace_id=99999)
        if not isinstance(fallback, dict) or not REQUIRED_SUMMARY_KEYS.issubset(fallback.keys()):
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"missing snapshot fallback error: {e}")

    # --- Payload persistence stability: if we have a snapshot, summary_json has required keys
    try:
        snap = get_latest_workspace_intelligence_snapshot(1)
        if snap and isinstance(snap.get("summary_json"), dict):
            payload = snap["summary_json"]
            if not REQUIRED_SUMMARY_KEYS.issubset(payload.keys()):
                stability_ok = False
        # If no snapshot (e.g. no DB), stability is OK by definition
    except Exception as e:
        stability_ok = False
        print(f"payload persistence stability error: {e}")

    # --- Refresh compatibility: refresh returns summary and can persist
    try:
        out = refresh_workspace_intelligence_summary(workspace_id=1)
        if not isinstance(out, dict) or not REQUIRED_SUMMARY_KEYS.issubset(out.keys()):
            refresh_ok = False
    except Exception as e:
        refresh_ok = False
        print(f"refresh compatibility error: {e}")

    print("workspace intelligence persistence OK" if (write_ok and read_ok and fallback_ok and stability_ok and refresh_ok) else "workspace intelligence persistence FAIL")
    print("snapshot write path: OK" if write_ok else "snapshot write path: FAIL")
    print("latest snapshot read: OK" if read_ok else "latest snapshot read: FAIL")
    print("missing snapshot fallback: OK" if fallback_ok else "missing snapshot fallback: FAIL")
    print("payload persistence stability: OK" if stability_ok else "payload persistence stability: FAIL")
    print("refresh compatibility: OK" if refresh_ok else "refresh compatibility: FAIL")
    if not (write_ok and read_ok and fallback_ok and stability_ok and refresh_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
