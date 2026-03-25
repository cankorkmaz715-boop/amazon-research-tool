#!/usr/bin/env python3
"""Step 129: Opportunity ranking stabilizer – raw vs stabilized score, volatility control, stability signals, board compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_stabilized_ranking, get_stabilized_rankings

    # Empty ref: returns structure with explanation
    out_empty = get_stabilized_ranking("")
    raw_vs_ok = (
        "opportunity_id" in out_empty
        and "raw_score" in out_empty
        and "stabilized_score" in out_empty
        and "explanation" in out_empty
    )

    # Nonexistent ref: raw 0, stabilized 0 or low, explanation present
    out_missing = get_stabilized_ranking("nonexistent-ref-129")
    raw_vs_ok = raw_vs_ok and (
        out_missing.get("opportunity_id") == "nonexistent-ref-129"
        and isinstance(out_missing.get("raw_score"), (int, float))
        and isinstance(out_missing.get("stabilized_score"), (int, float))
    )

    # Synthetic memory with spike: raw high, stabilized should be dampened by median blend
    mem = {
        "opportunity_ref": "smoke-129",
        "latest_opportunity_score": 85,
        "score_history": [
            {"at": "2025-01-01T00:00:00Z", "score": 55},
            {"at": "2025-01-02T00:00:00Z", "score": 58},
            {"at": "2025-01-03T00:00:00Z", "score": 52},
            {"at": "2025-01-04T00:00:00Z", "score": 60},
        ],
    }
    conf = {"confidence_label": "medium", "confidence_score": 55}
    out_synth = get_stabilized_ranking(
        "smoke-129",
        raw_score=85.0,
        memory_record=mem,
        confidence_record=conf,
    )
    volatility_ok = (
        out_synth.get("opportunity_id") == "smoke-129"
        and out_synth.get("raw_score") == 85.0
        and isinstance(out_synth.get("stabilized_score"), (int, float))
        and out_synth.get("stabilized_score") <= 85.0  # dampened
        and "median_blend" in (out_synth.get("explanation") or "")
    )

    # Stability signals in explanation
    stability_ok = bool(out_synth.get("explanation")) and "confidence=" in (out_synth.get("explanation") or "")

    # List API: returns list sorted by stabilized_score desc
    listing = get_stabilized_rankings(limit=5, workspace_id=None)
    board_ok = isinstance(listing, list)
    if listing:
        board_ok = (
            board_ok
            and all(
                "opportunity_id" in x and "stabilized_score" in x and "raw_score" in x
                for x in listing
            )
            and listing == sorted(listing, key=lambda x: -(x.get("stabilized_score") or 0))
        )

    print("opportunity ranking stabilizer OK")
    print("raw vs stabilized score: OK" if raw_vs_ok else "raw vs stabilized score: FAIL")
    print("volatility control: OK" if volatility_ok else "volatility control: FAIL")
    print("stability signals: OK" if stability_ok else "stability signals: FAIL")
    print("board compatibility: OK" if board_ok else "board compatibility: FAIL")

    if not (raw_vs_ok and volatility_ok and stability_ok and board_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
