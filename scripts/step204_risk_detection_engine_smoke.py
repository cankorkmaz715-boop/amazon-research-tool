#!/usr/bin/env python3
"""
Step 204 smoke test: Risk detection engine.
Validates risk generation, classification output, empty-state resilience, payload stability, isolation, fallback.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_TOP_KEYS = {
    "workspace_id",
    "generated_at",
    "risk_items",
    "high_risk_items",
    "medium_risk_items",
    "low_risk_items",
    "risk_summary",
    "rationale_summary",
    "top_risk_actions",
    "mitigation_suggestions",
    "confidence_indicators",
}
RISK_ENTRY_KEYS = {
    "item_type",
    "item_key",
    "risk_type",
    "risk_level",
    "rationale",
    "supporting_signals",
    "recommended_action",
    "mitigation_notes",
}
RISK_LEVELS = ("high", "medium", "low")


def main() -> None:
    from amazon_research.risk_detection import (
        generate_workspace_risk_detection,
        RISK_HIGH,
        RISK_MEDIUM,
        RISK_LOW,
    )
    from amazon_research.workspace_isolation import require_workspace_context

    gen_ok = True
    classification_ok = True
    empty_ok = True
    payload_ok = True
    isolation_ok = True
    fallback_ok = True

    # --- Risk generation: returns dict with required top-level keys
    try:
        out = generate_workspace_risk_detection(99991)
        if not isinstance(out, dict) or not REQUIRED_TOP_KEYS.issubset(out.keys()):
            gen_ok = False
        if out.get("workspace_id") != 99991:
            gen_ok = False
    except Exception as e:
        gen_ok = False
        print(f"risk generation error: {e}")

    # --- Classification output: risk_items entries have required fields; risk_level in allowed set
    try:
        out = generate_workspace_risk_detection(1)
        for entry in out.get("risk_items") or []:
            if not isinstance(entry, dict) or not RISK_ENTRY_KEYS.issubset(entry.keys()):
                classification_ok = False
                break
            lev = entry.get("risk_level")
            if lev not in RISK_LEVELS:
                classification_ok = False
        for lst in (out.get("high_risk_items") or [], out.get("medium_risk_items") or [], out.get("low_risk_items") or []):
            for e in lst:
                if e.get("risk_level") not in RISK_LEVELS:
                    classification_ok = False
    except Exception as e:
        classification_ok = False
        print(f"classification output error: {e}")

    # --- Empty-state resilience: None workspace returns stable shape; no crash
    try:
        empty_out = generate_workspace_risk_detection(None)
        if not isinstance(empty_out, dict) or not REQUIRED_TOP_KEYS.issubset(empty_out.keys()):
            empty_ok = False
        if (empty_out.get("high_risk_items") or []) != []:
            empty_ok = False
    except Exception as e:
        empty_ok = False
        print(f"empty-state resilience error: {e}")

    # --- Payload stability: risk_summary, rationale_summary, confidence_indicators correct types
    try:
        out = generate_workspace_risk_detection(99992)
        if not isinstance(out.get("risk_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("rationale_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("top_risk_actions"), list):
            payload_ok = False
        if not isinstance(out.get("mitigation_suggestions"), list):
            payload_ok = False
        if not isinstance(out.get("confidence_indicators"), dict):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    # --- Workspace isolation compatibility: require_workspace_context and workspace_id in output
    try:
        if not require_workspace_context(1, "risk_detection"):
            isolation_ok = False
        out = generate_workspace_risk_detection(1)
        if out.get("workspace_id") != 1:
            isolation_ok = False
    except Exception as e:
        isolation_ok = False
        print(f"workspace isolation compatibility error: {e}")

    # --- Fallback behavior: sparse/empty upstream yields stable shape; no crash
    try:
        out = generate_workspace_risk_detection(99993)
        if not isinstance(out, dict):
            fallback_ok = False
        if "risk_items" not in out or "high_risk_items" not in out:
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"fallback behavior error: {e}")

    print("risk detection engine OK")
    print("risk generation: OK" if gen_ok else "risk generation: FAIL")
    print("classification output: OK" if classification_ok else "classification output: FAIL")
    print("empty-state resilience: OK" if empty_ok else "empty-state resilience: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    print("workspace isolation compatibility: OK" if isolation_ok else "workspace isolation compatibility: FAIL")
    print("fallback behavior: OK" if fallback_ok else "fallback behavior: FAIL")
    if not all((gen_ok, classification_ok, empty_ok, payload_ok, isolation_ok, fallback_ok)):
        sys.exit(1)


if __name__ == "__main__":
    main()
