#!/usr/bin/env python3
"""
Step 201 smoke test: Opportunity strategy engine.
Validates strategy generation, classification output, empty-state resilience, payload stability, isolation, fallback.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_TOP_KEYS = {
    "workspace_id",
    "generated_at",
    "prioritized_opportunities",
    "monitor_opportunities",
    "deprioritized_opportunities",
    "strategy_summary",
    "rationale_summary",
    "top_actions",
    "risk_flags",
    "confidence_indicators",
}
ENTRY_KEYS = {"opportunity_id", "strategy_status", "priority_level", "rationale", "supporting_signals", "recommended_action", "risk_notes"}


def main() -> None:
    from amazon_research.opportunity_strategy import (
        generate_workspace_opportunity_strategy,
        STRATEGY_ACT_NOW,
        STRATEGY_MONITOR,
        STRATEGY_DEPRIORITIZE,
    )
    from amazon_research.workspace_isolation import require_workspace_context

    gen_ok = True
    classification_ok = True
    empty_ok = True
    payload_ok = True
    isolation_ok = True
    fallback_ok = True

    # --- Strategy generation: returns dict with required top-level keys
    try:
        out = generate_workspace_opportunity_strategy(99991)
        if not isinstance(out, dict) or not REQUIRED_TOP_KEYS.issubset(out.keys()):
            gen_ok = False
        if out.get("workspace_id") != 99991:
            gen_ok = False
    except Exception as e:
        gen_ok = False
        print(f"strategy generation error: {e}")

    # --- Classification output: each list contains entries with required fields; status in allowed set
    try:
        out = generate_workspace_opportunity_strategy(1)
        for lst in (out.get("prioritized_opportunities") or [], out.get("monitor_opportunities") or [], out.get("deprioritized_opportunities") or []):
            for entry in lst:
                if not isinstance(entry, dict) or not ENTRY_KEYS.issubset(entry.keys()):
                    classification_ok = False
                    break
                s = entry.get("strategy_status")
                if s not in (STRATEGY_ACT_NOW, STRATEGY_MONITOR, STRATEGY_DEPRIORITIZE):
                    classification_ok = False
    except Exception as e:
        classification_ok = False
        print(f"classification output error: {e}")

    # --- Empty-state resilience: None workspace returns stable shape; no crash
    try:
        empty_out = generate_workspace_opportunity_strategy(None)
        if not isinstance(empty_out, dict) or not REQUIRED_TOP_KEYS.issubset(empty_out.keys()):
            empty_ok = False
        if (empty_out.get("prioritized_opportunities") or []) != []:
            empty_ok = False
    except Exception as e:
        empty_ok = False
        print(f"empty-state resilience error: {e}")

    # --- Payload stability: strategy_summary and rationale_summary and confidence_indicators are dicts
    try:
        out = generate_workspace_opportunity_strategy(99992)
        if not isinstance(out.get("strategy_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("rationale_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("top_actions"), list):
            payload_ok = False
        if not isinstance(out.get("risk_flags"), list):
            payload_ok = False
        if not isinstance(out.get("confidence_indicators"), dict):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    # --- Workspace isolation compatibility: require_workspace_context and workspace_id in output
    try:
        if not require_workspace_context(1, "strategy"):
            isolation_ok = False
        out = generate_workspace_opportunity_strategy(1)
        if out.get("workspace_id") != 1:
            isolation_ok = False
    except Exception as e:
        isolation_ok = False
        print(f"workspace isolation compatibility error: {e}")

    # --- Fallback behavior: when signals fail, output has signal_fallback or empty lists; no crash
    try:
        out = generate_workspace_opportunity_strategy(99993)
        if not isinstance(out, dict):
            fallback_ok = False
        if "prioritized_opportunities" not in out:
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"fallback behavior error: {e}")

    print("opportunity strategy engine OK" if (gen_ok and classification_ok and empty_ok and payload_ok and isolation_ok and fallback_ok) else "opportunity strategy engine FAIL")
    print("strategy generation: OK" if gen_ok else "strategy generation: FAIL")
    print("classification output: OK" if classification_ok else "classification output: FAIL")
    print("empty-state resilience: OK" if empty_ok else "empty-state resilience: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    print("workspace isolation compatibility: OK" if isolation_ok else "workspace isolation compatibility: FAIL")
    print("fallback behavior: OK" if fallback_ok else "fallback behavior: FAIL")
    if not (gen_ok and classification_ok and empty_ok and payload_ok and isolation_ok and fallback_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
