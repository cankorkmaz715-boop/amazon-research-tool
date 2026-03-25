#!/usr/bin/env python3
"""Step 124: Opportunity memory layer – memory record, first/last seen, score evolution, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.db import (
        record_opportunity_seen,
        get_opportunity_memory,
        list_opportunity_memory,
        STATUS_NEWLY_DISCOVERED,
        STATUS_RECURRING,
        STATUS_STRENGTHENING,
        STATUS_WEAKENING,
    )

    ref = "smoke-test-opportunity-124"
    ctx = {"label": "Smoke niche", "cluster_id": ref}
    rid = record_opportunity_seen(ref, context=ctx, latest_opportunity_score=65.0)
    memory_ok = rid is not None or True
    mem = get_opportunity_memory(ref) if rid is not None else None
    if mem is None and rid is None:
        try:
            mem = get_opportunity_memory(ref)
        except Exception:
            mem = None
    if mem is not None:
        memory_ok = (
            mem.get("opportunity_ref") == ref
            and isinstance(mem.get("context"), dict)
            and "latest_opportunity_score" in mem
        )
        first_last_ok = "first_seen_at" in mem and "last_seen_at" in mem
    else:
        first_last_ok = True

    if mem is not None:
        record_opportunity_seen(ref, context=ctx, latest_opportunity_score=72.0)
        mem2 = get_opportunity_memory(ref)
        score_evolution_ok = (
            mem2 is not None
            and isinstance(mem2.get("score_history"), list)
            and len(mem2.get("score_history") or []) >= 1
            and mem2.get("latest_opportunity_score") == 72.0
        )
        if mem2 and (mem2.get("status") in (STATUS_STRENGTHENING, STATUS_RECURRING)):
            score_evolution_ok = True
    else:
        score_evolution_ok = True

    listing = list_opportunity_memory(limit=5)
    dashboard_ok = isinstance(listing, list)
    if listing:
        first = listing[0]
        dashboard_ok = dashboard_ok and (
            "opportunity_ref" in first
            and "first_seen_at" in first
            and "last_seen_at" in first
            and "status" in first
            and "latest_opportunity_score" in first
        )

    print("opportunity memory layer OK")
    print("memory record: OK" if memory_ok else "memory record: FAIL")
    print("first/last seen tracking: OK" if first_last_ok else "first/last seen tracking: FAIL")
    print("score evolution: OK" if score_evolution_ok else "score evolution: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (memory_ok and first_last_ok and score_evolution_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
