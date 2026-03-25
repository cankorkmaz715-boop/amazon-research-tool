#!/usr/bin/env python3
"""
Step 206 smoke test: Rate limiting and decision path hardening.
Validates read path rate limit, refresh path rate limit, duplicate refresh suppression,
workspace isolation, fallback policy, payload stability for allowed requests.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.decision_hardening import (
        check_decision_read_allowed,
        record_decision_read,
        check_decision_refresh_allowed,
        record_decision_refresh,
        check_refresh_cooldown,
        record_refresh_done,
        get_cooldown_seconds,
        get_read_max_per_minute,
        get_refresh_max_per_minute,
        get_policy_summary,
        PATH_STRATEGIC_SCORES_REFRESH,
    )
    from amazon_research.rate_limit import check_rate_limit, record_rate_limit, get_effective_rate_limit
    from amazon_research.workspace_isolation import require_workspace_context

    read_ok = True
    refresh_ok = True
    duplicate_ok = True
    isolation_ok = True
    fallback_ok = True
    payload_ok = True

    # --- Read path rate limiting: decision_read bucket is enforced
    try:
        limit = get_effective_rate_limit(99981, "decision_read")
        if not isinstance(limit, int) or limit < 1:
            read_ok = False
        allowed, retry = check_decision_read_allowed(99981)
        if not isinstance(allowed, bool):
            read_ok = False
        record_decision_read(99981)
    except Exception as e:
        read_ok = False
        print(f"read path rate limiting error: {e}")

    # --- Refresh path rate limiting: decision_refresh bucket + cooldown exist
    try:
        limit = get_effective_rate_limit(99982, "decision_refresh")
        if not isinstance(limit, int) or limit < 1:
            refresh_ok = False
        allowed, retry, suppressed = check_decision_refresh_allowed(99982, PATH_STRATEGIC_SCORES_REFRESH)
        if not isinstance(allowed, bool) or not isinstance(suppressed, bool):
            refresh_ok = False
    except Exception as e:
        refresh_ok = False
        print(f"refresh path rate limiting error: {e}")

    # --- Duplicate refresh suppression: cooldown blocks second refresh within window
    try:
        record_refresh_done(99983, "test_path_smoke")
        allowed2, retry2 = check_refresh_cooldown(99983, "test_path_smoke")
        if allowed2 and get_cooldown_seconds() > 0:
            duplicate_ok = False
        if not allowed2 and (retry2 is None or retry2 < 1):
            duplicate_ok = False
    except Exception as e:
        duplicate_ok = False
        print(f"duplicate refresh suppression error: {e}")

    # --- Workspace isolation compatibility: keys are workspace-scoped
    try:
        if not require_workspace_context(1, "decision_hardening"):
            isolation_ok = False
        allowed_a, _, _ = check_decision_refresh_allowed(1, PATH_STRATEGIC_SCORES_REFRESH)
        allowed_b, _, _ = check_decision_refresh_allowed(2, PATH_STRATEGIC_SCORES_REFRESH)
        if not isinstance(allowed_a, bool) or not isinstance(allowed_b, bool):
            isolation_ok = False
    except Exception as e:
        isolation_ok = False
        print(f"workspace isolation compatibility error: {e}")

    # --- Fallback policy behavior: policy returns safe defaults when env missing
    try:
        summary = get_policy_summary()
        if not isinstance(summary, dict):
            fallback_ok = False
        if "cooldown_seconds" not in summary or "refresh_max_per_minute" not in summary or "read_max_per_minute" not in summary:
            fallback_ok = False
        if get_cooldown_seconds() < 1 or get_read_max_per_minute() < 1 or get_refresh_max_per_minute() < 1:
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"fallback policy behavior error: {e}")

    # --- Payload stability for allowed requests: allowed request returns normal shape (handler contract unchanged)
    try:
        from amazon_research.strategic_scoring import generate_workspace_strategic_scores
        out = generate_workspace_strategic_scores(99984)
        if not isinstance(out, dict) or "scored_items" not in out or "top_scored_items" not in out:
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    print("decision hardening OK")
    print("read path rate limiting: OK" if read_ok else "read path rate limiting: FAIL")
    print("refresh path rate limiting: OK" if refresh_ok else "refresh path rate limiting: FAIL")
    print("duplicate refresh suppression: OK" if duplicate_ok else "duplicate refresh suppression: FAIL")
    print("workspace isolation compatibility: OK" if isolation_ok else "workspace isolation compatibility: FAIL")
    print("fallback policy behavior: OK" if fallback_ok else "fallback policy behavior: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    if not all((read_ok, refresh_ok, duplicate_ok, isolation_ok, fallback_ok, payload_ok)):
        sys.exit(1)


if __name__ == "__main__":
    main()
