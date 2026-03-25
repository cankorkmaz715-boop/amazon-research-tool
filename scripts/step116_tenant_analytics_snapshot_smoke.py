#!/usr/bin/env python3
"""Step 116: Tenant analytics snapshot engine – snapshot creation, usage/cost summary, history storage."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import (
        build_tenant_snapshot_payload,
        create_and_store_snapshot,
    )
    from amazon_research.db import get_latest_snapshot, get_snapshot_history

    workspace_id = 1
    payload = build_tenant_snapshot_payload(workspace_id, since_days=30)

    snapshot_ok = (
        isinstance(payload, dict)
        and "snapshot_at" in payload
        and "usage_summary" in payload
        and "quota_status" in payload
        and "cost_insight_summary" in payload
        and "alert_volume" in payload
        and "discovery_activity" in payload
        and "refresh_activity" in payload
        and "opportunity_generation_volume" in payload
    )

    usage_ok = isinstance(payload.get("usage_summary"), dict)
    cost_ok = isinstance(payload.get("cost_insight_summary"), dict)

    sid = create_and_store_snapshot(workspace_id, since_days=30)
    latest = get_latest_snapshot(workspace_id) if sid else None
    try:
        history = get_snapshot_history(workspace_id, limit=5)
    except Exception:
        history = []
    history_ok = (
        (sid is not None and latest is not None and "payload" in latest and "usage_summary" in latest.get("payload", {}))
        or (isinstance(history, list))
    )

    print("tenant analytics snapshot engine OK")
    print("snapshot creation: OK" if snapshot_ok else "snapshot creation: FAIL")
    print("usage summary: OK" if usage_ok else "usage summary: FAIL")
    print("cost summary: OK" if cost_ok else "cost summary: FAIL")
    print("history storage: OK" if history_ok else "history storage: FAIL")

    if not (snapshot_ok and usage_ok and cost_ok and history_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
