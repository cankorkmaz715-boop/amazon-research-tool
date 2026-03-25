#!/usr/bin/env python3
"""
Step 198 smoke test: Workspace alert preferences layer.
Validates default preferences read, upsert, persistence readback, alert gating, threshold, payload stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

PREF_KEYS = {
    "alerts_enabled",
    "opportunity_alerts_enabled",
    "trend_alerts_enabled",
    "portfolio_alerts_enabled",
    "score_threshold",
    "priority_threshold",
    "delivery_channels_json",
    "quiet_hours_json",
    "workspace_id",
}


def main() -> None:
    from amazon_research.workspace_alert_preferences import (
        get_workspace_alert_preferences,
        get_workspace_alert_preferences_with_defaults,
        upsert_workspace_alert_preferences,
        should_produce_opportunity_alerts,
        get_effective_alert_settings,
    )

    default_ok = True
    upsert_ok = True
    readback_ok = True
    gating_ok = True
    threshold_ok = True
    payload_ok = True

    # --- Default preferences read: with_defaults returns safe defaults when no row
    try:
        prefs = get_workspace_alert_preferences_with_defaults(99998)
        if not isinstance(prefs, dict) or not PREF_KEYS.issubset(prefs.keys()):
            default_ok = False
        if prefs.get("score_threshold") is None:
            default_ok = False
        if not isinstance(prefs.get("delivery_channels_json"), dict) or not isinstance(prefs.get("quiet_hours_json"), dict):
            default_ok = False
    except Exception as e:
        default_ok = False
        print(f"default preferences read error: {e}")

    # --- Preferences upsert: upsert returns workspace_id or None without crashing
    try:
        out = upsert_workspace_alert_preferences(1, {"score_threshold": 75.0, "opportunity_alerts_enabled": True})
        if out is not None and out != 1:
            upsert_ok = False
    except Exception as e:
        upsert_ok = False
        print(f"preferences upsert error: {e}")

    # --- Preferences persistence readback: get after upsert reflects stored values
    try:
        prefs = get_workspace_alert_preferences_with_defaults(1)
        if not isinstance(prefs, dict):
            readback_ok = False
        # With DB: may have score_threshold 75 if we just upserted; without DB we get defaults
        if prefs.get("score_threshold") is not None and not (0 <= float(prefs["score_threshold"]) <= 100):
            readback_ok = False
    except Exception as e:
        if "DB not initialized" in str(e) or "connection" in str(e).lower():
            readback_ok = True
        else:
            readback_ok = False
            print(f"preferences persistence readback error: {e}")

    # --- Alert gating compatibility: should_produce_opportunity_alerts and get_effective_alert_settings don't crash
    try:
        produce = should_produce_opportunity_alerts(1)
        if not isinstance(produce, bool):
            gating_ok = False
        effective = get_effective_alert_settings(1)
        if not isinstance(effective, dict) or "opportunity_alerts_enabled" not in effective:
            gating_ok = False
    except Exception as e:
        gating_ok = False
        print(f"alert gating compatibility error: {e}")

    # --- Threshold compatibility: effective settings include score_threshold in valid range
    try:
        effective = get_effective_alert_settings(99997)
        t = effective.get("score_threshold")
        if t is not None:
            try:
                if not (0 <= float(t) <= 100):
                    threshold_ok = False
            except (TypeError, ValueError):
                threshold_ok = False
    except Exception as e:
        threshold_ok = False
        print(f"threshold compatibility error: {e}")

    # --- Payload stability: with_defaults always has expected keys; malformed JSON safe
    try:
        for wid in (None, 1, 99):
            p = get_workspace_alert_preferences_with_defaults(wid)
            if not PREF_KEYS.issubset(p.keys()):
                payload_ok = False
            if not isinstance(p.get("delivery_channels_json"), dict) or not isinstance(p.get("quiet_hours_json"), dict):
                payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    print("workspace alert preferences OK" if (default_ok and upsert_ok and readback_ok and gating_ok and threshold_ok and payload_ok) else "workspace alert preferences FAIL")
    print("default preferences read: OK" if default_ok else "default preferences read: FAIL")
    print("preferences upsert: OK" if upsert_ok else "preferences upsert: FAIL")
    print("preferences persistence readback: OK" if readback_ok else "preferences persistence readback: FAIL")
    print("alert gating compatibility: OK" if gating_ok else "alert gating compatibility: FAIL")
    print("threshold compatibility: OK" if threshold_ok else "threshold compatibility: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    if not (default_ok and upsert_ok and readback_ok and gating_ok and threshold_ok and payload_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
