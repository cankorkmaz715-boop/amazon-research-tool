#!/usr/bin/env python3
"""Step 127: Opportunity explainability layer – signal aggregation, explanation generation, attribution, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_opportunity_explanation, list_explanations

    # Missing ref: should return structure with empty/message summary
    out_empty = get_opportunity_explanation("")
    signal_agg_ok = (
        "opportunity_id" in out_empty
        and "main_supporting_signals" in out_empty
        and "explanation_summary" in out_empty
        and "signal_contribution_overview" in out_empty
        and isinstance(out_empty.get("main_supporting_signals"), dict)
        and isinstance(out_empty.get("signal_contribution_overview"), list)
    )

    # Nonexistent ref: still returns full structure, explanation from available (empty) signals
    out_missing = get_opportunity_explanation("nonexistent-ref-127")
    explanation_ok = (
        out_missing.get("opportunity_id") == "nonexistent-ref-127"
        and isinstance(out_missing.get("explanation_summary"), str)
        and len(out_missing.get("explanation_summary", "")) >= 0
    )

    # With synthetic memory + lifecycle: check attribution and summary
    mem = {
        "opportunity_ref": "smoke-127",
        "context": {"demand_score": 70, "competition_score": 35, "label": "Test niche"},
        "latest_opportunity_score": 65,
        "status": "recurring",
    }
    lifecycle = {
        "lifecycle_state": "stable",
        "supporting_signals": {"score_trend": "flat"},
    }
    out_synth = get_opportunity_explanation(
        "smoke-127",
        memory_record=mem,
        lifecycle_record=lifecycle,
    )
    attr_ok = (
        out_synth.get("opportunity_id") == "smoke-127"
        and out_synth.get("main_supporting_signals", {}).get("demand_score") == 70
        and out_synth.get("main_supporting_signals", {}).get("competition_score") == 35
        and out_synth.get("main_supporting_signals", {}).get("opportunity_index") == 65
        and out_synth.get("main_supporting_signals", {}).get("lifecycle_state") == "stable"
        and any(
            c.get("signal") == "demand" and c.get("contribution") == "positive"
            for c in out_synth.get("signal_contribution_overview", [])
        )
    )

    # List: returns list of explanation dicts
    listing = list_explanations(limit=5, workspace_id=None)
    dashboard_ok = isinstance(listing, list)
    if listing:
        first = listing[0]
        dashboard_ok = (
            dashboard_ok
            and "opportunity_id" in first
            and "explanation_summary" in first
            and "main_supporting_signals" in first
        )

    print("opportunity explainability layer OK")
    print("signal aggregation: OK" if signal_agg_ok else "signal aggregation: FAIL")
    print("explanation generation: OK" if explanation_ok else "explanation generation: FAIL")
    print("signal attribution: OK" if attr_ok else "signal attribution: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (signal_agg_ok and explanation_ok and attr_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
