#!/usr/bin/env python3
"""Step 177: Workspace risk/reward map – risk estimation, reward estimation, quadrant classification, portfolio compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.discovery.risk_reward_map import (
        get_risk_reward_for_opportunity,
        get_workspace_risk_reward_map,
        get_risk_reward_for_portfolio_item,
        QUADRANT_LOW_RISK_LOW_REWARD,
        QUADRANT_LOW_RISK_HIGH_REWARD,
        QUADRANT_HIGH_RISK_HIGH_REWARD,
        QUADRANT_HIGH_RISK_LOW_REWARD,
        QUADRANTS,
    )

    # 1) Risk estimation: risk_score 0-100, influenced by competition and lifecycle
    out_high_risk = get_risk_reward_for_opportunity(
        "risk-ref-1",
        lifecycle_output={"lifecycle_state": "weakening", "lifecycle_score": 30, "supporting_signal_summary": {"score_trend": "down"}},
        competition_score=80,
    )
    risk_ok = (
        isinstance(out_high_risk.get("risk_score"), (int, float))
        and 0 <= out_high_risk["risk_score"] <= 100
        and "signal_summary" in out_high_risk
    )

    # 2) Reward estimation: reward_score 0-100, influenced by demand and lifecycle
    out_high_reward = get_risk_reward_for_opportunity(
        "reward-ref-1",
        lifecycle_output={"lifecycle_state": "rising", "lifecycle_score": 75, "supporting_signal_summary": {"score_trend": "up"}},
        demand_score=70,
        opportunity_score=72,
    )
    reward_ok = (
        isinstance(out_high_reward.get("reward_score"), (int, float))
        and 0 <= out_high_reward["reward_score"] <= 100
        and out_high_reward.get("reward_score") >= 50
    )

    # 3) Quadrant classification: one of four quadrants
    quadrant_ok = out_high_risk.get("quadrant_classification") in QUADRANTS
    quadrant_ok = quadrant_ok and out_high_reward.get("quadrant_classification") in QUADRANTS
    low_risk_low = get_risk_reward_for_opportunity(
        "q-ref",
        competition_score=30,
        demand_score=40,
        lifecycle_output={"lifecycle_state": "maturing", "lifecycle_score": 45, "supporting_signal_summary": {"score_trend": "flat"}},
    )
    quadrant_ok = quadrant_ok and low_risk_low.get("quadrant_classification") in QUADRANTS

    # 4) Portfolio compatibility: get_workspace_risk_reward_map and get_risk_reward_for_portfolio_item
    map_list = get_workspace_risk_reward_map(workspace_id=1, limit=10)
    portfolio_ok = isinstance(map_list, list)
    if map_list:
        first = map_list[0]
        portfolio_ok = (
            portfolio_ok
            and "opportunity_id" in first
            and "risk_score" in first
            and "reward_score" in first
            and "quadrant_classification" in first
            and "timestamp" in first
        )
    portfolio_item = {"target_entity": {"ref": "port-ref-1", "type": "opportunity"}}
    single = get_risk_reward_for_portfolio_item(portfolio_item)
    portfolio_ok = portfolio_ok and single.get("opportunity_id") == "port-ref-1" and "risk_score" in single

    print("risk reward map OK")
    print("risk estimation: OK" if risk_ok else "risk estimation: FAIL")
    print("reward estimation: OK" if reward_ok else "reward estimation: FAIL")
    print("quadrant classification: OK" if quadrant_ok else "quadrant classification: FAIL")
    print("portfolio compatibility: OK" if portfolio_ok else "portfolio compatibility: FAIL")

    if not (risk_ok and reward_ok and quadrant_ok and portfolio_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
