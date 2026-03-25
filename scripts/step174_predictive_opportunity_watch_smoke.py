#!/usr/bin/env python3
"""Step 174: Predictive opportunity watch – watch candidate detection, lifecycle integration, trend monitoring, workspace compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.discovery.predictive_opportunity_watch import (
        get_predictive_watch,
        list_predictive_watch_candidates,
        to_feed_item,
        CLASS_EARLY_WATCH,
        CLASS_WATCHLIST,
        CLASS_RISING_CANDIDATE,
        WATCH_CLASSIFICATIONS,
    )

    # 1) Watch candidate detection: required fields and valid classification
    life_rising = {"lifecycle_state": "rising", "lifecycle_score": 72, "supporting_signal_summary": {}}
    out = get_predictive_watch(
        "watch-ref-1",
        lifecycle_output=life_rising,
        trend_direction="up",
        demand_trend="up",
    )
    detection_ok = (
        out.get("opportunity_id") == "watch-ref-1"
        and out.get("watch_classification") in WATCH_CLASSIFICATIONS
        and isinstance(out.get("predictive_confidence"), (int, float))
        and isinstance(out.get("signal_summary"), dict)
        and "timestamp" in out
    )
    detection_ok = detection_ok and out.get("watch_classification") == CLASS_RISING_CANDIDATE

    # 2) Lifecycle integration: emerging -> early_watch
    life_emerging = {"lifecycle_state": "emerging", "lifecycle_score": 45, "supporting_signal_summary": {}}
    out2 = get_predictive_watch("watch-ref-2", lifecycle_output=life_emerging, trend_direction="flat")
    lifecycle_ok = out2.get("watch_classification") in (CLASS_EARLY_WATCH, CLASS_WATCHLIST)
    lifecycle_ok = lifecycle_ok and "lifecycle_state" in (out2.get("signal_summary") or {})

    # 3) Trend monitoring: score_trend and trend_direction in signal_summary
    mem = {"opportunity_ref": "watch-ref-3", "score_history": [40, 45, 50]}
    out3 = get_predictive_watch("watch-ref-3", memory_record=mem)
    trend_ok = "score_trend" in (out3.get("signal_summary") or {}) and "trend_direction" in (out3.get("signal_summary") or {})

    # 4) Workspace compatibility: list_predictive_watch_candidates and to_feed_item
    listed = list_predictive_watch_candidates(workspace_id=None, limit=5)
    workspace_ok = isinstance(listed, list)
    feed_item = to_feed_item(out, workspace_id=1)
    workspace_ok = (
        workspace_ok
        and isinstance(feed_item, dict)
        and feed_item.get("feed_item_type") == "predictive_watch"
        and "target_entity" in feed_item
        and "predictive_confidence" in feed_item
        and feed_item.get("watch_classification") == CLASS_RISING_CANDIDATE
    )

    print("predictive opportunity watch OK")
    print("watch candidate detection: OK" if detection_ok else "watch candidate detection: FAIL")
    print("lifecycle integration: OK" if lifecycle_ok else "lifecycle integration: FAIL")
    print("trend monitoring: OK" if trend_ok else "trend monitoring: FAIL")
    print("workspace compatibility: OK" if workspace_ok else "workspace compatibility: FAIL")

    if not (detection_ok and lifecycle_ok and trend_ok and workspace_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
