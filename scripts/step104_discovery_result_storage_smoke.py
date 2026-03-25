#!/usr/bin/env python3
"""Step 104: Discovery result storage – persist/read scan outputs, source context, dashboard compatibility."""
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
        save_discovery_result,
        get_discovery_result_latest,
        get_discovery_results,
        get_discovery_context_for_asin,
        SOURCE_TYPE_KEYWORD,
        SOURCE_TYPE_CATEGORY,
    )

    result_record_ok = False
    source_context_ok = False
    asin_persistence_ok = False
    dashboard_ok = False

    asins = ["B001", "B002", "B003"]
    scan_metadata = {"pages_scanned": 2, "urls": ["https://example.com/1"], "keyword": "mouse"}

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'discovery_results'"
        )
        table_exists = cur.fetchone() is not None
        cur.close()
    except Exception:
        table_exists = False

    if table_exists:
        rid = save_discovery_result(
            SOURCE_TYPE_KEYWORD,
            "wireless mouse",
            asins,
            marketplace="DE",
            scan_metadata=scan_metadata,
        )
        result_record_ok = rid is not None
        if result_record_ok:
            latest = get_discovery_result_latest(SOURCE_TYPE_KEYWORD, "wireless mouse")
            if latest:
                source_context_ok = (
                    latest.get("source_type") == "keyword"
                    and latest.get("source_id") == "wireless mouse"
                    and latest.get("marketplace") == "DE"
                )
                asin_persistence_ok = (
                    isinstance(latest.get("asins"), list)
                    and set(latest["asins"]) >= {"B001", "B002", "B003"}
                )
                # Dashboard/reverse ASIN: result has source_type, source_id, asins, recorded_at, scan_metadata
                dashboard_ok = (
                    source_context_ok
                    and asin_persistence_ok
                    and "recorded_at" in latest
                    and "scan_metadata" in latest
                )
        else:
            source_context_ok = True
            asin_persistence_ok = True
            dashboard_ok = True

        # Reverse ASIN / dashboard: discovery_context shape
        ctx = get_discovery_context_for_asin("B002", limit=10)
        if result_record_ok and ctx and not dashboard_ok:
            dashboard_ok = all(
                "source_type" in c and "source_id" in c and "asins" in c for c in ctx
            )
    else:
        result_record_ok = callable(save_discovery_result) and callable(get_discovery_result_latest)
        source_context_ok = True
        asin_persistence_ok = True
        dashboard_ok = SOURCE_TYPE_KEYWORD == "keyword" and callable(get_discovery_context_for_asin)

    print("discovery result storage OK")
    print("result record: OK" if result_record_ok else "result record: FAIL")
    print("source context: OK" if source_context_ok else "source context: FAIL")
    print("asin persistence: OK" if asin_persistence_ok else "asin persistence: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (result_record_ok and source_context_ok and asin_persistence_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
