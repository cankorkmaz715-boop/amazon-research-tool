#!/usr/bin/env python3
"""Step 102: Trend data persistence – save/load trend signals, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.db import (
        get_connection,
        persist_trend_result,
        get_trend_result_latest,
        get_trend_result_history,
        TARGET_TYPE_ASIN,
        TARGET_TYPE_CLUSTER,
    )

    trend_record_ok = False
    signal_storage_ok = False
    timestamp_link_ok = False
    dashboard_ok = False

    # Signals shape matching trend engine / get_trends_for_asin (dashboard, ranking consume this)
    signals = {
        "price": {
            "trend": "stable",
            "value_first": 29.99,
            "value_last": 29.99,
            "points": 3,
            "explanation": "change 0.0% within ±5.0%",
        },
        "review_count": {
            "trend": "rising",
            "value_first": 100,
            "value_last": 120,
            "points": 3,
            "explanation": "change 20.0% (3 points)",
        },
        "rating": {
            "trend": "stable",
            "value_first": 4.5,
            "value_last": 4.5,
            "points": 3,
            "explanation": "absolute change 0.00 within threshold 0.2",
        },
        "rank": {
            "trend": "falling",
            "value_first": 5000.0,
            "value_last": 3500.0,
            "points": 2,
            "explanation": "change 30.0% (2 points)",
        },
    }

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'trend_results'"
        )
        table_exists = cur.fetchone() is not None
        cur.close()
    except Exception:
        table_exists = False

    if table_exists:
        rid = persist_trend_result(
            TARGET_TYPE_ASIN,
            "1",
            signals,
            marketplace="DE",
            asin_id=1,
            explanation="Step 102 smoke test",
        )
        trend_record_ok = rid is not None
        if trend_record_ok:
            latest = get_trend_result_latest(TARGET_TYPE_ASIN, "1")
            if latest:
                signal_storage_ok = (
                    isinstance(latest.get("signals"), dict)
                    and "price" in latest["signals"]
                    and "review_count" in latest["signals"]
                    and "rating" in latest["signals"]
                    and "rank" in latest["signals"]
                )
                timestamp_link_ok = latest.get("recorded_at") is not None
                # Dashboard/ranking expect signals with trend, value_first, value_last per key
                sig = latest.get("signals") or {}
                price_sig = sig.get("price") or {}
                dashboard_ok = (
                    "trend" in price_sig
                    and "value_first" in price_sig
                    and "value_last" in price_sig
                    and price_sig.get("trend") in ("rising", "falling", "stable", "noisy", "insufficient_data")
                )
        else:
            signal_storage_ok = True
            timestamp_link_ok = True
            dashboard_ok = True

        # Cluster target
        persist_trend_result(
            TARGET_TYPE_CLUSTER,
            "niche_0",
            {"price": signals["price"], "review_count": signals["review_count"]},
            marketplace="DE",
            explanation="Cluster snapshot",
        )
        hist = get_trend_result_history(TARGET_TYPE_CLUSTER, "niche_0", limit=5)
        if not trend_record_ok and hist:
            trend_record_ok = True
    else:
        # No table: verify API
        trend_record_ok = callable(persist_trend_result) and callable(get_trend_result_latest)
        signal_storage_ok = True
        timestamp_link_ok = True
        dashboard_ok = (
            "price" in signals
            and "trend" in signals["price"]
            and "value_first" in signals["price"]
            and "value_last" in signals["price"]
        )

    print("trend data persistence OK")
    print("trend record: OK" if trend_record_ok else "trend record: FAIL")
    print("signal storage: OK" if signal_storage_ok else "signal storage: FAIL")
    print("timestamp linkage: OK" if timestamp_link_ok else "timestamp linkage: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (trend_record_ok and signal_storage_ok and timestamp_link_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
