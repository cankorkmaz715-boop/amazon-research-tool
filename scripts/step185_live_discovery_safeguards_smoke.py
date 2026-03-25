#!/usr/bin/env python3
"""Step 185: Live discovery safeguards – target caps, duplicate suppression, cooldown, market safety."""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.scheduler.live_discovery_safeguards import (
        evaluate_target,
        evaluate_safeguards,
        get_default_safeguard_context,
        record_target_scanned,
        DECISION_ALLOW,
        DECISION_DEFER,
        DECISION_REJECT,
    )

    target_caps_ok = False
    duplicate_ok = False
    cooldown_ok = False
    market_safety_ok = False

    # 1) Target caps: max_targets_per_cycle and per_market_cap enforced
    try:
        ctx = get_default_safeguard_context()
        ctx["max_targets_per_cycle"] = 3
        ctx["per_market_cap"] = 2
        candidates = [
            {"market": "DE", "target_type": "keyword", "target_id": "kw1"},
            {"market": "DE", "target_type": "keyword", "target_id": "kw2"},
            {"market": "DE", "target_type": "keyword", "target_id": "kw3"},
            {"market": "US", "target_type": "keyword", "target_id": "kw4"},
        ]
        result = evaluate_safeguards(candidates, context=ctx)
        allowed = result.get("allowed") or []
        deferred = result.get("deferred") or []
        target_caps_ok = len(allowed) <= 3 and result.get("counts", {}).get("allowed", 0) <= 3
        # DE should be capped at 2 (per_market_cap), so at most 2 DE + 1 US = 3 allowed
        de_count = sum(1 for a in allowed if (a.get("market") or "").upper() == "DE")
        target_caps_ok = target_caps_ok and de_count <= 2
        target_caps_ok = target_caps_ok and all(
            "safeguard_decision" in d and "safeguard_reason" in d and "timestamp" in d
            for d in result.get("decisions") or []
        )
    except Exception as e:
        print(f"target caps FAIL: {e}")
        target_caps_ok = False

    # 2) Duplicate suppression: same target twice -> second rejected
    try:
        ctx = get_default_safeguard_context()
        ctx["max_targets_per_cycle"] = 10
        ctx["per_market_cap"] = 10
        candidates = [
            {"market": "AU", "target_type": "category", "target_id": "https://www.amazon.com.au/s"},
            {"market": "AU", "target_type": "category", "target_id": "https://www.amazon.com.au/s"},
        ]
        result = evaluate_safeguards(candidates, context=ctx)
        allowed = result.get("allowed") or []
        rejected = result.get("rejected") or []
        duplicate_ok = len(allowed) == 1 and any(
            r.get("safeguard_reason") == "duplicate_target" for r in rejected
        )
    except Exception as e:
        print(f"duplicate suppression FAIL: {e}")
        duplicate_ok = False

    # 3) Cooldown handling: record_target_scanned then evaluate same target -> defer
    try:
        record_target_scanned("US", "keyword", "cooldown_test")
        ctx = get_default_safeguard_context()
        ctx["cooldown_seconds"] = 600
        ctx["max_targets_per_cycle"] = 10
        dec = evaluate_target("US", "keyword", "cooldown_test", context=ctx)
        cooldown_ok = dec.get("safeguard_decision") == DECISION_DEFER and "cooldown" in (dec.get("safeguard_reason") or "").lower()
        # Also test empty target_id -> reject
        empty_dec = evaluate_target("DE", "keyword", "", context=ctx)
        cooldown_ok = cooldown_ok and empty_dec.get("safeguard_decision") == DECISION_REJECT
    except Exception as e:
        print(f"cooldown handling FAIL: {e}")
        cooldown_ok = False

    # 4) Market safety: decisions have market, target_type, target_id, safeguard_decision, safeguard_reason, timestamp
    try:
        ctx = get_default_safeguard_context()
        dec = evaluate_target("AU", "category", "https://www.amazon.com.au/gp/bestsellers", context=ctx)
        market_safety_ok = (
            dec.get("market") == "AU"
            and dec.get("target_type") == "category"
            and (dec.get("target_id") or "") != ""
            and dec.get("safeguard_decision") in (DECISION_ALLOW, DECISION_DEFER, DECISION_REJECT)
            and "safeguard_reason" in dec
            and "timestamp" in dec
        )
        result = evaluate_safeguards(
            [{"market": "DE", "target_type": "keyword", "target_id": "safe"}],
            context=ctx,
        )
        market_safety_ok = market_safety_ok and all(
            "market" in d and "target_type" in d and "target_id" in d
            for d in result.get("decisions") or []
        )
    except Exception as e:
        print(f"market safety FAIL: {e}")
        market_safety_ok = False

    all_ok = target_caps_ok and duplicate_ok and cooldown_ok and market_safety_ok
    print("live discovery safeguards OK" if all_ok else "live discovery safeguards FAIL")
    print("target caps: OK" if target_caps_ok else "target caps: FAIL")
    print("duplicate suppression: OK" if duplicate_ok else "duplicate suppression: FAIL")
    print("cooldown handling: OK" if cooldown_ok else "cooldown handling: FAIL")
    print("market safety: OK" if market_safety_ok else "market safety: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
