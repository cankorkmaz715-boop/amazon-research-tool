#!/usr/bin/env python3
"""
Step 203 smoke test: Market entry signals engine.
Validates market signal generation, classification output, empty-state resilience, payload stability, isolation, fallback.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

REQUIRED_TOP_KEYS = {
    "workspace_id",
    "generated_at",
    "market_signals",
    "recommended_markets",
    "monitor_markets",
    "deprioritized_markets",
    "market_entry_summary",
    "rationale_summary",
    "top_market_actions",
    "risk_flags",
    "confidence_indicators",
}
SIGNAL_ENTRY_KEYS = {
    "market_key",
    "recommendation_status",
    "priority_level",
    "rationale",
    "supporting_signals",
    "recommended_action",
    "risk_notes",
}
RECOMMEND_STATUSES = ("enter_now", "monitor_market", "defer_market")


def main() -> None:
    from amazon_research.market_entry_signals import (
        generate_workspace_market_entry_signals,
        STATUS_ENTER_NOW,
        STATUS_MONITOR,
        STATUS_DEFER,
    )
    from amazon_research.workspace_isolation import require_workspace_context

    gen_ok = True
    classification_ok = True
    empty_ok = True
    payload_ok = True
    isolation_ok = True
    fallback_ok = True

    # --- Market signal generation: returns dict with required top-level keys
    try:
        out = generate_workspace_market_entry_signals(99991)
        if not isinstance(out, dict) or not REQUIRED_TOP_KEYS.issubset(out.keys()):
            gen_ok = False
        if out.get("workspace_id") != 99991:
            gen_ok = False
    except Exception as e:
        gen_ok = False
        print(f"market signal generation error: {e}")

    # --- Classification output: market_signals entries have required fields; status in allowed set
    try:
        out = generate_workspace_market_entry_signals(1)
        for entry in out.get("market_signals") or []:
            if not isinstance(entry, dict) or not SIGNAL_ENTRY_KEYS.issubset(entry.keys()):
                classification_ok = False
                break
            s = entry.get("recommendation_status")
            if s not in RECOMMEND_STATUSES:
                classification_ok = False
        for lst in (out.get("recommended_markets") or [], out.get("monitor_markets") or [], out.get("deprioritized_markets") or []):
            for e in lst:
                if e.get("recommendation_status") not in RECOMMEND_STATUSES:
                    classification_ok = False
    except Exception as e:
        classification_ok = False
        print(f"classification output error: {e}")

    # --- Empty-state resilience: None workspace returns stable shape; no crash
    try:
        empty_out = generate_workspace_market_entry_signals(None)
        if not isinstance(empty_out, dict) or not REQUIRED_TOP_KEYS.issubset(empty_out.keys()):
            empty_ok = False
        if (empty_out.get("recommended_markets") or []) != []:
            empty_ok = False
    except Exception as e:
        empty_ok = False
        print(f"empty-state resilience error: {e}")

    # --- Payload stability: market_entry_summary, rationale_summary, confidence_indicators correct types
    try:
        out = generate_workspace_market_entry_signals(99992)
        if not isinstance(out.get("market_entry_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("rationale_summary"), dict):
            payload_ok = False
        if not isinstance(out.get("top_market_actions"), list):
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
        if not require_workspace_context(1, "market_entry_signals"):
            isolation_ok = False
        out = generate_workspace_market_entry_signals(1)
        if out.get("workspace_id") != 1:
            isolation_ok = False
    except Exception as e:
        isolation_ok = False
        print(f"workspace isolation compatibility error: {e}")

    # --- Fallback behavior: sparse/empty upstream yields stable shape; no crash
    try:
        out = generate_workspace_market_entry_signals(99993)
        if not isinstance(out, dict):
            fallback_ok = False
        if "market_signals" not in out or "recommended_markets" not in out:
            fallback_ok = False
    except Exception as e:
        fallback_ok = False
        print(f"fallback behavior error: {e}")

    print("market entry signals engine OK")
    print("market signal generation: OK" if gen_ok else "market signal generation: FAIL")
    print("classification output: OK" if classification_ok else "classification output: FAIL")
    print("empty-state resilience: OK" if empty_ok else "empty-state resilience: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    print("workspace isolation compatibility: OK" if isolation_ok else "workspace isolation compatibility: FAIL")
    print("fallback behavior: OK" if fallback_ok else "fallback behavior: FAIL")
    if not all((gen_ok, classification_ok, empty_ok, payload_ok, isolation_ok, fallback_ok)):
        sys.exit(1)


if __name__ == "__main__":
    main()
