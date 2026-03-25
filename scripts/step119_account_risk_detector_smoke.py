#!/usr/bin/env python3
"""Step 119: Account risk detector – risk score, risk label, signal explanation, ops compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

VALID_LABELS = ("low", "elevated", "high", "critical")


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.monitoring import get_account_risk

    workspace_id = 1
    result = get_account_risk(workspace_id, since_days=30)

    risk_score_ok = (
        isinstance(result.get("risk_score"), (int, float))
        and 0 <= result["risk_score"] <= 100
    )

    risk_label_ok = (result.get("risk_label") or "").strip() in VALID_LABELS

    signals = result.get("risk_signals") or {}
    signal_ok = (
        "explanation" in result
        and isinstance(result.get("explanation"), str)
        and isinstance(signals, dict)
        and "workspace_health_score" in signals
        and "quota_pressure" in signals
        and "worker_queue_ops" in signals
    )

    ops_ok = (
        result.get("workspace_id") == workspace_id
        and "risk_score" in result
        and "risk_label" in result
        and "risk_signals" in result
        and "workspace_health_status" in signals
        and "alert_intensity" in signals
    )

    print("account risk detector OK")
    print("risk score: OK" if risk_score_ok else "risk score: FAIL")
    print("risk label: OK" if risk_label_ok else "risk label: FAIL")
    print("signal explanation: OK" if signal_ok else "signal explanation: FAIL")
    print("ops compatibility: OK" if ops_ok else "ops compatibility: FAIL")

    if not (risk_score_ok and risk_label_ok and signal_ok and ops_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
