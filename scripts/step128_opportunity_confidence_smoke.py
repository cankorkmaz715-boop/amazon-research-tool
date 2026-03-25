#!/usr/bin/env python3
"""Step 128: Opportunity confidence scoring – confidence calculation, label, signal consistency, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

LABELS = ("low", "medium", "high")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_opportunity_confidence, list_opportunities_with_confidence

    # Empty ref: returns structure with low confidence and explanation
    out_empty = get_opportunity_confidence("")
    calc_ok = (
        "opportunity_id" in out_empty
        and "confidence_score" in out_empty
        and "confidence_label" in out_empty
        and "explanation" in out_empty
        and "contributing_signals" in out_empty
        and isinstance(out_empty.get("confidence_score"), (int, float))
        and out_empty.get("confidence_label") in LABELS
    )

    # Nonexistent ref: score 0–100, valid label
    out_missing = get_opportunity_confidence("nonexistent-ref-128")
    label_ok = (
        out_missing.get("opportunity_id") == "nonexistent-ref-128"
        and out_missing.get("confidence_label") in LABELS
        and 0 <= out_missing.get("confidence_score", -1) <= 100
    )

    # Synthetic memory + explanation: check contributing_signals and consistency
    mem = {
        "opportunity_ref": "smoke-128",
        "score_history": [{"at": "2025-01-01T00:00:00Z", "score": 60}, {"at": "2025-01-02T00:00:00Z", "score": 65}],
        "context": {"demand_score": 70, "competition_score": 40},
    }
    explanation_record = {
        "signal_contribution_overview": [
            {"signal": "demand", "value": "70", "contribution": "positive"},
            {"signal": "competition", "value": "40", "contribution": "positive"},
            {"signal": "opportunity_index", "value": "65", "contribution": "positive"},
        ],
    }
    out_synth = get_opportunity_confidence(
        "smoke-128",
        memory_record=mem,
        explanation_record=explanation_record,
    )
    consistency_ok = (
        out_synth.get("opportunity_id") == "smoke-128"
        and isinstance(out_synth.get("contributing_signals"), dict)
        and "supporting_data_count" in out_synth.get("contributing_signals", {})
        and "repeated_detections" in out_synth.get("contributing_signals", {})
        and "signal_consistency" in out_synth.get("contributing_signals", {})
        and out_synth.get("contributing_signals", {}).get("signal_consistency", {}).get("positive") == 3
    )

    # List: returns list with confidence dict on each item
    listing = list_opportunities_with_confidence(limit=5, workspace_id=None)
    dashboard_ok = isinstance(listing, list)
    if listing:
        first = listing[0]
        dashboard_ok = (
            dashboard_ok
            and "confidence" in first
            and isinstance(first["confidence"], dict)
            and first["confidence"].get("confidence_label") in LABELS
            and "explanation" in first["confidence"]
        )

    print("opportunity confidence scoring OK")
    print("confidence calculation: OK" if calc_ok else "confidence calculation: FAIL")
    print("confidence label: OK" if label_ok else "confidence label: FAIL")
    print("signal consistency: OK" if consistency_ok else "signal consistency: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (calc_ok and label_ok and consistency_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
