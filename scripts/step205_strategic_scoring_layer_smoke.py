#!/usr/bin/env python3
"""
Step 205 smoke test: Strategic scoring layer.
Validates strategic score generation, classification output, risk-adjusted scoring, empty-state, payload stability, isolation, fallback.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_TOP_KEYS = {
    "workspace_id",
    "generated_at",
    "scored_items",
    "top_scored_items",
    "score_summary",
    "rationale_summary",
    "top_strategic_actions",
    "risk_adjustment_notes",
    "confidence_indicators",
}
SCORED_ENTRY_KEYS = {
    "item_type",
    "item_key",
    "item_label",
    "strategic_score",
    "strategic_band",
    "rationale",
    "supporting_signals",
    "recommended_action",
    "risk_adjustment_notes",
}
BANDS = ("strong", "moderate", "weak")


def main() -> None:
    from amazon_research.strategic_scoring import (
        generate_workspace_strategic_scores,
        BAND_STRONG,
        BAND_MODERATE,
        BAND_WEAK,
    )
    from amazon_research.workspace_isolation import require_workspace_context

    gen_ok = True
    classification_ok = True
    risk_adjusted_ok = True
    empty_ok = True
    payload_ok = True
    isolation_ok = True
    fallback_ok = True

    # --- Strategic score generation: returns dict with required top-level keys
    try:
        out = generate_workspace_strategic_scores(99991)
        if not isinstance(out, dict) or not REQUIRED_TOP_KEYS.issubset(out.keys()):
            gen_ok = False
        if out.get("workspace_id") != 99991:
            gen_ok = False
    except Exception as e:
        gen_ok = False
        print(f"strategic score generation error: {e}")

    # --- Score classification output: scored_items have required fields; strategic_band in allowed set
    try:
        out = generate_workspace_strategic_scores(1)
        for entry in out.get("scored_items") or []:
            if not isinstance(entry, dict) or not SCORED_ENTRY_KEYS.issubset(entry.keys()):
                classification_ok = False
                break
            band = entry.get("strategic_band")
            if band not in BANDS:
                classification_ok = False
            score = entry.get("strategic_score")
            if score is not None and (score < 0 or score > 100):
                classification_ok = False
    except Exception as e:
        classification_ok = False
        print(f"score classification output error: {e}")

    # --- Risk-adjusted scoring: score_summary includes risk_penalty_applied; items can have risk_adjustment_notes
    try:
        out = generate_workspace_strategic_scores(99992)
        summary = out.get("score_summary") or {}
        if "risk_penalty_applied" not in summary:
            risk_adjusted_ok = False
        if not isinstance(out.get("risk_adjustment_notes"), list):
            risk_adjusted_ok = False
        for item in out.get("scored_items") or []:
            if "risk_adjustment_notes" not in item:
                risk_adjusted_ok = False
                break
    except Exception as e:
        risk_adjusted_ok = False
        print(f"risk-adjusted scoring error: {e}")

    # --- Empty-state resilience: None workspace returns stable shape; no crash
    try:
        empty_out = generate_workspace_strategic_scores(None)
        if not isinstance(empty_out, dict) or not REQUIRED_TOP_KEYS.issubset(empty_out.keys()):
            empty_ok = False
        if (empty_out.get("scored_items") or []) != []:
            empty_ok = False
    except Exception as e:
        empty_ok = False
        print(f"empty-state resilience error: {e}")

    # --- Payload stability: score_summary, rationale_summary, confidence_indicators correct types
    try:
        out = generate_workspace_strategic_scores(99993)
        if not isinstance(out.get("score_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("rationale_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("top_strategic_actions"), list):
            payload_ok = False
        if not isinstance(out.get("confidence_indicators"), dict):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    # --- Workspace isolation compatibility: require_workspace_context and workspace_id in output
    try:
        if not require_workspace_context(1, "strategic_scoring"):
            isolation_ok = False
        out = generate_workspace_strategic_scores(1)
        if out.get("workspace_id") != 1:
            isolation_ok = False
    except Exception as e:
        isolation_ok = False
        print(f"workspace isolation compatibility error: {e}")

    # --- Fallback behavior: sparse upstream yields stable shape; no crash
    try:
        out = generate_workspace_strategic_scores(99994)
        if not isinstance(out, dict):
            fallback_ok = False
        if "scored_items" not in out or "top_scored_items" not in out:
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"fallback behavior error: {e}")

    print("strategic scoring layer OK")
    print("strategic score generation: OK" if gen_ok else "strategic score generation: FAIL")
    print("score classification output: OK" if classification_ok else "score classification output: FAIL")
    print("risk-adjusted scoring: OK" if risk_adjusted_ok else "risk-adjusted scoring: FAIL")
    print("empty-state resilience: OK" if empty_ok else "empty-state resilience: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    print("workspace isolation compatibility: OK" if isolation_ok else "workspace isolation compatibility: FAIL")
    print("fallback behavior: OK" if fallback_ok else "fallback behavior: FAIL")
    if not all((gen_ok, classification_ok, risk_adjusted_ok, empty_ok, payload_ok, isolation_ok, fallback_ok)):
        sys.exit(1)


if __name__ == "__main__":
    main()
