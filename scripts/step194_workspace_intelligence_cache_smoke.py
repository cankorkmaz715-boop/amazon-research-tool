#!/usr/bin/env python3
"""
Step 194 smoke test: Workspace intelligence cache layer.
Validates cache read, miss fallback, warm, refresh/invalidation, payload stability, resilience.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_KEYS = {
    "workspace_id", "summary_timestamp", "total_tracked_opportunities",
    "active_high_priority_count", "new_opportunities_recent_window",
    "average_opportunity_score", "top_opportunity_refs", "trend_overview",
    "alert_overview", "category_coverage_overview", "market_coverage_overview",
}


def main() -> None:
    from amazon_research.workspace_intelligence import (
        get_cached_summary,
        set_cached_summary,
        invalidate_cached_summary,
        get_workspace_intelligence_summary_prefer_cached,
        refresh_workspace_intelligence_summary,
    )

    read_ok = True
    fallback_ok = True
    warm_ok = True
    invalidation_ok = True
    payload_ok = True
    resilience_ok = True

    # --- Cache read path: set then get returns same payload
    try:
        dummy = {k: (0 if k in ("total_tracked_opportunities", "active_high_priority_count", "new_opportunities_recent_window") else (0.0 if k == "average_opportunity_score" else ([] if k == "top_opportunity_refs" else {}))) for k in REQUIRED_KEYS}
        dummy["workspace_id"] = 1
        dummy["summary_timestamp"] = "2025-03-14T12:00:00+00:00"
        set_cached_summary(1, dummy)
        got = get_cached_summary(1)
        if got is None or not REQUIRED_KEYS.issubset(got.keys()):
            read_ok = False
    except Exception as e:
        read_ok = False
        print(f"cache read path error: {e}")

    # --- Cache miss fallback: prefer_cached with no/wrong cache returns from persistence or compute
    try:
        invalidate_cached_summary(99)
        out = get_workspace_intelligence_summary_prefer_cached(99)
        if not isinstance(out, dict) or not REQUIRED_KEYS.issubset(out.keys()):
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"cache miss fallback error: {e}")

    # --- Cache warm path: after prefer_cached (compute fallback), cache is warmed for next read
    try:
        invalidate_cached_summary(98)
        get_workspace_intelligence_summary_prefer_cached(98)
        hit = get_cached_summary(98)
        if hit is None:
            warm_ok = False
        if hit and not REQUIRED_KEYS.issubset(hit.keys()):
            warm_ok = False
    except Exception as e:
        warm_ok = False
        print(f"cache warm path error: {e}")

    # --- Cache refresh invalidation: invalidate removes; refresh warms (set then get)
    try:
        dummy97 = {k: (0 if k in ("total_tracked_opportunities", "active_high_priority_count", "new_opportunities_recent_window") else (0.0 if k == "average_opportunity_score" else ([] if k == "top_opportunity_refs" else {}))) for k in REQUIRED_KEYS}
        dummy97["workspace_id"] = 97
        dummy97["summary_timestamp"] = "2025-01-01T00:00:00+00:00"
        set_cached_summary(97, dummy97)
        invalidate_cached_summary(97)
        if get_cached_summary(97) is not None:
            invalidation_ok = False
        refresh_workspace_intelligence_summary(97)
        if get_cached_summary(97) is None:
            invalidation_ok = False
    except Exception as e:
        invalidation_ok = False
        print(f"cache refresh invalidation error: {e}")

    # --- Payload stability: summary from cache and from prefer_cached have same shape
    try:
        s1 = get_cached_summary(1)
        s2 = get_workspace_intelligence_summary_prefer_cached(1)
        if s1 is not None and not REQUIRED_KEYS.issubset(s1.keys()):
            payload_ok = False
        if not isinstance(s2, dict) or not REQUIRED_KEYS.issubset(s2.keys()):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    # --- Cache resilience: None/invalid workspace_id doesn't crash; get returns None
    try:
        if get_cached_summary(None) is not None:
            resilience_ok = False
        set_cached_summary(None, {})
        invalidate_cached_summary(None)
        out = get_workspace_intelligence_summary_prefer_cached(None)
        if not isinstance(out, dict) or out.get("workspace_id") is not None:
            resilience_ok = False
    except Exception as e:
        resilience_ok = False
        print(f"cache resilience error: {e}")

    print("workspace intelligence cache OK" if (read_ok and fallback_ok and warm_ok and invalidation_ok and payload_ok and resilience_ok) else "workspace intelligence cache FAIL")
    print("cache read path: OK" if read_ok else "cache read path: FAIL")
    print("cache miss fallback: OK" if fallback_ok else "cache miss fallback: FAIL")
    print("cache warm path: OK" if warm_ok else "cache warm path: FAIL")
    print("cache refresh invalidation: OK" if invalidation_ok else "cache refresh invalidation: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    print("cache resilience: OK" if resilience_ok else "cache resilience: FAIL")
    if not (read_ok and fallback_ok and warm_ok and invalidation_ok and payload_ok and resilience_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
