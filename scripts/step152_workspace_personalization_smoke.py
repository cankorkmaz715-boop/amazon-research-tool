#!/usr/bin/env python3
"""Step 152: Workspace personalization signals – preference inference, market preference, opportunity preference, dashboard compatibility."""
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

    from amazon_research.monitoring import get_workspace_personalization_signals

    out = get_workspace_personalization_signals(1)

    # 1) Preference inference: personalization_signal_set and preference_summary
    signal_set = out.get("personalization_signal_set") or {}
    pref_ok = (
        isinstance(signal_set, dict)
        and "preference_summary" in out
        and len(out.get("preference_summary") or "") > 0
    )

    # 2) Market preference: preferred_markets in signal set
    market_ok = "preferred_markets" in signal_set and isinstance(signal_set.get("preferred_markets"), list)

    # 3) Opportunity preference: preferred_opportunity_pattern, confidence_tolerance
    opp_ok = (
        "preferred_opportunity_pattern" in signal_set
        and "confidence_tolerance" in signal_set
    )

    # 4) Dashboard compatibility: workspace_id, signal_strengths, timestamp
    strengths = out.get("signal_strengths") or {}
    dashboard_ok = (
        out.get("workspace_id") == 1
        and "timestamp" in out
        and isinstance(strengths, dict)
    )

    print("workspace personalization signals OK")
    print("preference inference: OK" if pref_ok else "preference inference: FAIL")
    print("market preference: OK" if market_ok else "market preference: FAIL")
    print("opportunity preference: OK" if opp_ok else "opportunity preference: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (pref_ok and market_ok and opp_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
