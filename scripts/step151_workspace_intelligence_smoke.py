#!/usr/bin/env python3
"""Step 151: SaaS workspace intelligence layer – focus area detection, market activity, behavior patterns, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    try:
        from amazon_research.db import init_db
        init_db()
    except Exception:
        pass

    from amazon_research.monitoring import get_workspace_intelligence

    # Run intelligence for workspace 1 (may have no data; structure still required)
    out = get_workspace_intelligence(1)

    # 1) Focus area detection: focus_areas_summary with expected shape
    focus = out.get("focus_areas_summary") or {}
    focus_ok = (
        isinstance(focus, dict)
        and "top_niche_cluster_terms" in focus
        and "watchlist_by_type" in focus
        and "session_count" in focus
        and "thread_count" in focus
    )

    # 2) Market activity summary
    market = out.get("market_activity_summary") or {}
    market_ok = (
        isinstance(market, dict)
        and "markets_mentioned" in market
        and "mention_counts" in market
    )

    # 3) Behavior patterns: research_behavior_summary and notable_patterns_or_tendencies
    behavior = out.get("research_behavior_summary") or {}
    patterns = out.get("notable_patterns_or_tendencies") or []
    behavior_ok = (
        isinstance(behavior, dict)
        and "total_sessions" in behavior
        and "intent_distribution" in behavior
        and isinstance(patterns, list)
    )

    # 4) Dashboard compatibility: workspace_id, timestamp, all summary keys present
    dashboard_ok = (
        out.get("workspace_id") == 1
        and "timestamp" in out
        and "focus_areas_summary" in out
        and "market_activity_summary" in out
        and "research_behavior_summary" in out
        and "notable_patterns_or_tendencies" in out
    )

    print("workspace intelligence layer OK")
    print("focus area detection: OK" if focus_ok else "focus area detection: FAIL")
    print("market activity summary: OK" if market_ok else "market activity summary: FAIL")
    print("behavior patterns: OK" if behavior_ok else "behavior patterns: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (focus_ok and market_ok and behavior_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
