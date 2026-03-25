#!/usr/bin/env python3
"""Step 89: Market opportunity index – index generation, signal normalization, cluster comparison, board compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.clustering import cluster_products
    from amazon_research.board import build_opportunity_board
    from amazon_research.ranking import rank_cluster_opportunities
    from amazon_research.index import build_market_opportunity_index

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    rank_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    moi_out = build_market_opportunity_index(clusters, asin_pool=asin_pool, use_db=False)
    index_results = moi_out.get("index_results") or []
    summary = moi_out.get("summary") or {}

    # --- Index generation: results produced with MOI fields ---
    gen_ok = (
        isinstance(index_results, list)
        and len(index_results) >= 1
        and all(
            "cluster_id" in r and "market_opportunity_index" in r and "moi_tier" in r
            for r in index_results
        )
    )

    # --- Signal normalization: index 0–100, batch_normalized_moi when applicable ---
    norm_ok = all(
        isinstance(r.get("market_opportunity_index"), (int, float))
        and 0 <= r.get("market_opportunity_index", -1) <= 100
        and r.get("moi_tier") in ("low", "medium", "high")
        for r in index_results
    )
    if index_results and index_results[0].get("batch_normalized_moi") is not None:
        norm_ok = norm_ok and all(
            0 <= (r.get("batch_normalized_moi") or 0) <= 100 for r in index_results
        )

    # --- Cluster comparison: multiple clusters can be ordered by MOI ---
    moi_values = [r["market_opportunity_index"] for r in index_results]
    comparison_ok = (
        len(moi_values) == len(clusters)
        and moi_values == sorted(moi_values, reverse=True)
    )

    # --- Board compatibility: every index cluster_id appears in board entries ---
    board_out = build_opportunity_board(clusters, ranking_result=rank_out)
    entries = board_out.get("entries") or []
    board_cids = {e["cluster_id"] for e in entries}
    board_compat_ok = all(r["cluster_id"] in board_cids for r in index_results) and len(index_results) == len(entries)

    print("market opportunity index OK")
    print("index generation: OK" if gen_ok else "index generation: FAIL")
    print("signal normalization: OK" if norm_ok else "signal normalization: FAIL")
    print("cluster comparison: OK" if comparison_ok else "cluster comparison: FAIL")
    print("board compatibility: OK" if board_compat_ok else "board compatibility: FAIL")

    if not (gen_ok and norm_ok and comparison_ok and board_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
