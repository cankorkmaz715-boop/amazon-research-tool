#!/usr/bin/env python3
"""Step 153: Personalized opportunity ranking – base vs personalized score, workspace adjustment, preference application, dashboard compatibility."""
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

    from amazon_research.discovery import (
        get_personalized_ranking,
        list_personalized_rankings,
        get_recommendations,
    )

    # 1) Base vs personalized score: single opportunity ranking has both fields
    entry = get_personalized_ranking("test-opportunity-153", workspace_id=1)
    base_pers_ok = (
        "base_opportunity_score" in entry
        and "personalized_score" in entry
        and entry.get("target_opportunity_id") == "test-opportunity-153"
    )
    # Base and personalized can be equal when no adjustments
    base_val = entry.get("base_opportunity_score")
    pers_val = entry.get("personalized_score")
    base_pers_ok = base_pers_ok and base_val is not None and pers_val is not None

    # 2) Workspace adjustment: workspace_id in output and list_personalized_rankings(workspace_id)
    workspace_ok = entry.get("workspace_id") == 1
    listed = list_personalized_rankings(1, limit=10)
    workspace_ok = workspace_ok and isinstance(listed, list)
    if listed:
        workspace_ok = workspace_ok and all(r.get("workspace_id") == 1 for r in listed)

    # 3) Preference application: personalization_explanation present (may be empty or describe adjustments)
    pref_ok = "personalization_explanation" in entry and isinstance(entry.get("personalization_explanation"), str)

    # 4) Dashboard compatibility: timestamp, all required keys
    dashboard_ok = (
        "timestamp" in entry
        and "target_opportunity_id" in entry
        and "base_opportunity_score" in entry
        and "personalized_score" in entry
    )

    print("personalized opportunity ranking OK")
    print("base vs personalized score: OK" if base_pers_ok else "base vs personalized score: FAIL")
    print("workspace adjustment: OK" if workspace_ok else "workspace adjustment: FAIL")
    print("preference application: OK" if pref_ok else "preference application: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (base_pers_ok and workspace_ok and pref_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
