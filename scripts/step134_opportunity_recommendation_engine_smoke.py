#!/usr/bin/env python3
"""Step 134: Opportunity recommendation engine – recommendation generation, priority scoring, explanation, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_recommendations

    # Generate recommendations (may be empty if no data)
    recos = get_recommendations(workspace_id=1, limit=10, include_watchlist=True, include_alerts=True)
    gen_ok = isinstance(recos, list)

    # Each item has required fields
    priority_ok = True
    explanation_ok = True
    for r in recos:
        if not (
            "recommendation_id" in r
            and "target_entity" in r
            and "recommendation_type" in r
            and "priority_score" in r
            and "explanation" in r
            and "timestamp" in r
        ):
            gen_ok = False
        if "priority_score" in r:
            ps = r["priority_score"]
            if not (isinstance(ps, (int, float)) and 0 <= ps <= 100):
                priority_ok = False
        if "explanation" in r:
            if not isinstance(r["explanation"], str):
                explanation_ok = False
        if "target_entity" in r:
            te = r["target_entity"]
            if not (isinstance(te, dict) and "type" in te and "ref" in te):
                gen_ok = False

    # If we got any recommendations, check ordering (desc by priority_score)
    if len(recos) >= 2:
        priority_ok = priority_ok and recos[0].get("priority_score", 0) >= recos[1].get("priority_score", 100)

    # Dashboard: list with consistent shape
    dashboard_ok = True
    if recos:
        first = recos[0]
        dashboard_ok = (
            first.get("recommendation_id", "").startswith("rec-")
            and isinstance(first.get("target_entity"), dict)
            and "recommendation_type" in first
        )

    print("opportunity recommendation engine OK")
    print("recommendation generation: OK" if gen_ok else "recommendation generation: FAIL")
    print("priority scoring: OK" if priority_ok else "priority scoring: FAIL")
    print("explanation output: OK" if explanation_ok else "explanation output: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (gen_ok and priority_ok and explanation_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
