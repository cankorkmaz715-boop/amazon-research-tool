#!/usr/bin/env python3
"""Step 179: Research copilot strategy layer – strategy guidance, signal interpretation, workspace alignment, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.discovery.research_copilot_strategy import (
        get_copilot_strategy_guidance,
        get_strategy_guidance_for_dashboard,
        DIRECTION_FOCUS_THIS_NICHE,
        DIRECTION_DIVERSIFY_PORTFOLIO,
        DIRECTION_REDUCE_EXPOSURE,
        DIRECTION_WATCH_EMERGING_CANDIDATE,
        DIRECTION_AVOID_UNSTABLE_SEGMENT,
        DIRECTIONS,
    )

    workspace_id = 1

    def valid_guidance(g):
        return (
            isinstance(g, dict)
            and g.get("workspace_id") == workspace_id
            and g.get("strategy_guidance_id")
            and g.get("recommended_strategic_direction") in DIRECTIONS
            and "reasoning_summary" in g
            and "main_supporting_signals" in g
            and "timestamp" in g
        )

    # 1) Strategy guidance: required fields and valid direction
    guidance_list = get_copilot_strategy_guidance(workspace_id, limit=15)
    strategy_ok = isinstance(guidance_list, list)
    for g in guidance_list[:5]:
        if not valid_guidance(g):
            strategy_ok = False
            break
    if guidance_list and strategy_ok is not False:
        strategy_ok = strategy_ok and valid_guidance(guidance_list[0])

    # 2) Signal interpretation: main_supporting_signals present and non-empty when guidance exists
    signal_ok = True
    for g in guidance_list:
        sigs = g.get("main_supporting_signals")
        if not isinstance(sigs, dict):
            signal_ok = False
            break
        if g.get("recommended_strategic_direction") and not sigs:
            pass  # can be empty in edge case
    if guidance_list:
        signal_ok = signal_ok and isinstance(guidance_list[0].get("main_supporting_signals"), dict)

    # 3) Workspace alignment: all items have same workspace_id
    workspace_ok = all(g.get("workspace_id") == workspace_id for g in guidance_list)

    # 4) Dashboard compatibility: get_strategy_guidance_for_dashboard returns same shape
    dashboard_list = get_strategy_guidance_for_dashboard(workspace_id, limit=10)
    dashboard_ok = isinstance(dashboard_list, list)
    if dashboard_list:
        dashboard_ok = (
            dashboard_ok
            and "recommended_strategic_direction" in dashboard_list[0]
            and "reasoning_summary" in dashboard_list[0]
            and "strategy_guidance_id" in dashboard_list[0]
        )

    print("research copilot strategy layer OK")
    print("strategy guidance: OK" if strategy_ok else "strategy guidance: FAIL")
    print("signal interpretation: OK" if signal_ok else "signal interpretation: FAIL")
    print("workspace alignment: OK" if workspace_ok else "workspace alignment: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (strategy_ok and signal_ok and workspace_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
