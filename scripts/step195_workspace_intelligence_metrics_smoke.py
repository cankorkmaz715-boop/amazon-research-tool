#!/usr/bin/env python3
"""
Step 195 smoke test: Workspace intelligence metrics layer.
Validates read tracking, cache metrics, fallback metrics, refresh metrics, payload stability, resilience.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_TOP_KEYS = {
    "generated_at",
    "read_metrics",
    "cache_metrics",
    "snapshot_metrics",
    "refresh_metrics",
    "fallback_metrics",
    "performance_metrics",
}


def main() -> None:
    from amazon_research.workspace_intelligence import (
        get_workspace_intelligence_metrics_summary,
        reset_workspace_intelligence_metrics_for_test_only,
        get_workspace_intelligence_summary_prefer_cached,
        run_workspace_intelligence_refresh_cycle,
    )
    from amazon_research.workspace_intelligence.metrics import (
        record_read,
        record_cache_hit,
        record_cache_miss,
        record_snapshot_hit,
        record_compute_fallback,
        record_refresh_attempt,
        record_refresh_success,
        record_refresh_failure,
    )

    read_ok = True
    cache_ok = True
    fallback_ok = True
    refresh_ok = True
    payload_ok = True
    resilience_ok = True

    reset_workspace_intelligence_metrics_for_test_only()

    # --- Read tracking: record_read then summary shows total_reads
    try:
        record_read()
        record_read()
        s = get_workspace_intelligence_metrics_summary()
        if s.get("read_metrics", {}).get("total_reads", 0) < 2:
            read_ok = False
    except Exception as e:
        read_ok = False
        print(f"read tracking error: {e}")

    # --- Cache metrics: record cache hit/miss then summary has cache_metrics
    try:
        record_cache_hit()
        record_cache_miss()
        s = get_workspace_intelligence_metrics_summary()
        cm = s.get("cache_metrics") or {}
        if cm.get("cache_hits", 0) < 1 or cm.get("cache_misses", 0) < 1:
            cache_ok = False
    except Exception as e:
        cache_ok = False
        print(f"cache metrics error: {e}")

    # --- Fallback metrics: record snapshot hit and compute fallback
    try:
        record_snapshot_hit()
        record_compute_fallback()
        s = get_workspace_intelligence_metrics_summary()
        fm = s.get("fallback_metrics") or {}
        sm = s.get("snapshot_metrics") or {}
        if fm.get("compute_fallbacks", 0) < 1 or sm.get("snapshot_hits", 0) < 1:
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"fallback metrics error: {e}")

    # --- Refresh metrics: record refresh attempt/success/failure
    try:
        record_refresh_attempt()
        record_refresh_success(1.5)
        record_refresh_failure()
        s = get_workspace_intelligence_metrics_summary()
        rm = s.get("refresh_metrics") or {}
        if rm.get("refresh_attempts", 0) < 1 or rm.get("refresh_successes", 0) < 1 or rm.get("refresh_failures", 0) < 1:
            refresh_ok = False
    except Exception as e:
        refresh_ok = False
        print(f"refresh metrics error: {e}")

    # --- Payload stability: summary has all required top-level keys and nested shape
    try:
        s = get_workspace_intelligence_metrics_summary()
        if not REQUIRED_TOP_KEYS.issubset(s.keys()):
            payload_ok = False
        if not isinstance(s.get("performance_metrics"), dict):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    # --- Metrics resilience: prefer_cached and refresh_cycle don't crash when metrics used; get summary never raises
    try:
        get_workspace_intelligence_summary_prefer_cached(1)
        run_workspace_intelligence_refresh_cycle(batch_limit=1)
        _ = get_workspace_intelligence_metrics_summary()
    except Exception as e:
        resilience_ok = False
        print(f"metrics resilience error: {e}")

    print("workspace intelligence metrics OK" if (read_ok and cache_ok and fallback_ok and refresh_ok and payload_ok and resilience_ok) else "workspace intelligence metrics FAIL")
    print("read tracking: OK" if read_ok else "read tracking: FAIL")
    print("cache metrics: OK" if cache_ok else "cache metrics: FAIL")
    print("fallback metrics: OK" if fallback_ok else "fallback metrics: FAIL")
    print("refresh metrics: OK" if refresh_ok else "refresh metrics: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    print("metrics resilience: OK" if resilience_ok else "metrics resilience: FAIL")
    if not (read_ok and cache_ok and fallback_ok and refresh_ok and payload_ok and resilience_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
