#!/usr/bin/env python3
"""Step 83: Market opportunity board – board generation, ranked entries, signal display, dashboard readiness."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.clustering import cluster_products
    from amazon_research.ranking import rank_cluster_opportunities
    from amazon_research.board import build_opportunity_board

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    ranking_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    board_out = build_opportunity_board(clusters, ranking_result=ranking_out)

    entries = board_out.get("entries") or []
    summary = board_out.get("summary") or {}

    # --- Board generation: entries produced ---
    gen_ok = isinstance(entries, list) and len(entries) >= 1

    # --- Ranked entries: each has cluster_id, label, opportunity_score, member_count ---
    ranked_ok = all(
        isinstance(e, dict)
        and "cluster_id" in e
        and "label" in e
        and "opportunity_score" in e
        and "member_count" in e
        for e in entries
    )

    # --- Signal display structure: core_signals present with expected keys ---
    core_keys = {"cluster_size", "has_niche_context"}
    signals_ok = all(
        isinstance(e.get("core_signals"), dict) and core_keys <= set(e.get("core_signals", {}))
        for e in entries
    )

    # --- Dashboard readiness: clean shape, summary ---
    dashboard_ok = (
        "summary" in board_out
        and isinstance(summary, dict)
        and "total" in summary
        and (not entries or all("opportunity_score" in e and "member_count" in e for e in entries))
    )

    print("market opportunity board OK")
    print("board generation: OK" if gen_ok else "board generation: FAIL")
    print("ranked entries: OK" if ranked_ok else "ranked entries: FAIL")
    print("signal display structure: OK" if signals_ok else "signal display structure: FAIL")
    print("dashboard readiness: OK" if dashboard_ok else "dashboard readiness: FAIL")

    if not (gen_ok and ranked_ok and signals_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
