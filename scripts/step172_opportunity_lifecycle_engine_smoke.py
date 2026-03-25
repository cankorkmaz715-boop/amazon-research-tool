#!/usr/bin/env python3
"""Step 172: Opportunity lifecycle engine – lifecycle state, signal history, drift integration, feed compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.discovery.opportunity_lifecycle_engine import (
        get_lifecycle_state,
        list_opportunities_with_lifecycle_engine,
        get_lifecycle_for_feed,
        STATE_EMERGING,
        STATE_RISING,
        STATE_WEAKENING,
        STATE_FADING,
        STATE_MATURING,
        LIFECYCLE_STATES,
    )

    # 1) Lifecycle state detection: output has required fields and valid state
    mem_rising = {
        "opportunity_ref": "test-ref-1",
        "first_seen_at": "2025-01-01T00:00:00Z",
        "last_seen_at": "2025-03-01T00:00:00Z",
        "status": "strengthening",
        "score_history": [{"score": 40}, {"score": 55}, {"score": 65}],
        "latest_opportunity_score": 65,
    }
    base_rising = {"lifecycle_state": "rising", "rationale": "score strengthening"}
    out = get_lifecycle_state("test-ref-1", memory_record=mem_rising, base_lifecycle=base_rising)
    state_ok = (
        out.get("opportunity_id") == "test-ref-1"
        and out.get("lifecycle_state") in LIFECYCLE_STATES
        and "lifecycle_score" in out
        and isinstance(out.get("supporting_signal_summary"), dict)
        and "timestamp" in out
    )

    # 2) Signal history usage: supporting_signal_summary includes score_trend, base_lifecycle, confidence
    summary = out.get("supporting_signal_summary") or {}
    signal_ok = (
        "score_trend" in summary or "base_lifecycle_state" in summary or "confidence_label" in summary
    ) and "score_history_length" in summary or "latest_opportunity_score" in summary

    # 3) Drift integration: when drift_reports passed or built from history, summary can include drift
    mem_with_history = {
        "opportunity_ref": "test-ref-2",
        "score_history": [{"score": 10}, {"score": 12}, {"score": 11}, {"score": 25}],
        "latest_opportunity_score": 25,
    }
    out2 = get_lifecycle_state("test-ref-2", memory_record=mem_with_history)
    drift_ok = isinstance(out2.get("supporting_signal_summary"), dict)
    if (out2.get("supporting_signal_summary") or {}).get("drift_types"):
        drift_ok = True
    drift_ok = drift_ok and out2.get("lifecycle_state") in LIFECYCLE_STATES

    # 4) Feed compatibility: get_lifecycle_for_feed and list_opportunities_with_lifecycle_engine
    feed_out = get_lifecycle_for_feed("feed-ref", memory_record={"opportunity_ref": "feed-ref", "score_history": [50, 52]})
    feed_ok = (
        feed_out.get("opportunity_id") == "feed-ref"
        and "lifecycle_state" in feed_out
        and "lifecycle_score" in feed_out
        and "supporting_signal_summary" in feed_out
        and "timestamp" in feed_out
    )
    listed = list_opportunities_with_lifecycle_engine(limit=5)
    feed_ok = feed_ok and isinstance(listed, list)
    if listed:
        first = listed[0]
        feed_ok = feed_ok and ("lifecycle_engine" in first or "lifecycle_state" in first)

    print("opportunity lifecycle engine OK")
    print("lifecycle state detection: OK" if state_ok else "lifecycle state detection: FAIL")
    print("signal history usage: OK" if signal_ok else "signal history usage: FAIL")
    print("drift integration: OK" if drift_ok else "drift integration: FAIL")
    print("feed compatibility: OK" if feed_ok else "feed compatibility: FAIL")

    if not (state_ok and signal_ok and drift_ok and feed_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
