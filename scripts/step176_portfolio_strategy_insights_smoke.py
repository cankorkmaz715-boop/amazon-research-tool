#!/usr/bin/env python3
"""Step 176: Portfolio strategy insights – portfolio analysis, concentration, strategy summary, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.discovery.portfolio_strategy_insights import (
        get_portfolio_strategy_insights,
        get_insights_for_dashboard,
    )

    workspace_id = 1

    # 1) Portfolio analysis: required fields and structure
    insights = get_portfolio_strategy_insights(workspace_id)
    analysis_ok = (
        isinstance(insights, dict)
        and insights.get("workspace_id") == workspace_id
        and "portfolio_insight_id" in insights
        and "portfolio_health_summary" in insights
        and "strategy_summary" in insights
        and "timestamp" in insights
    )

    # 2) Concentration detection: metrics when portfolio non-empty
    if insights.get("metrics"):
        m = insights["metrics"]
        concentration_ok = "concentration_ratio" in m and "is_concentrated" in m
    else:
        concentration_ok = True
    concentration_ok = concentration_ok and isinstance(insights.get("portfolio_health_summary"), str)

    # 3) Strategy summary: strengths, weaknesses, suggested_portfolio_actions
    strategy_ok = (
        isinstance(insights.get("strengths"), list)
        and isinstance(insights.get("weaknesses"), list)
        and isinstance(insights.get("suggested_portfolio_actions"), list)
    )

    # 4) Dashboard compatibility: get_insights_for_dashboard and structure
    dashboard_insights = get_insights_for_dashboard(workspace_id, limit=50)
    dashboard_ok = (
        isinstance(dashboard_insights, dict)
        and dashboard_insights.get("workspace_id") == workspace_id
        and "portfolio_health_summary" in dashboard_insights
        and "suggested_portfolio_actions" in dashboard_insights
    )

    print("portfolio strategy insights OK")
    print("portfolio analysis: OK" if analysis_ok else "portfolio analysis: FAIL")
    print("concentration detection: OK" if concentration_ok else "concentration detection: FAIL")
    print("strategy summary: OK" if strategy_ok else "strategy summary: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (analysis_ok and concentration_ok and strategy_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
