#!/usr/bin/env python3
"""Step 88: Opportunity signal fusion – signal merge, opportunity score, explanation, board compatibility."""
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
    from amazon_research.fusion import fuse_opportunity_signals

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    rank_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    fused_out = fuse_opportunity_signals(clusters, asin_pool=asin_pool, use_db=False)
    fused = fused_out.get("fused_results") or []

    # --- Signal merge: contributing_signals has ranking, demand, competition, trend, niche ---
    expected_keys = {"ranking_score", "demand_score", "competition_score", "trend_score", "niche_score"}
    merge_ok = all(
        isinstance(r.get("contributing_signals"), dict)
        and expected_keys <= set(r.get("contributing_signals", {}))
        for r in fused
    )

    # --- Opportunity score: each has fused_opportunity_score in 0–100 ---
    score_ok = all(
        isinstance(r.get("fused_opportunity_score"), (int, float))
        and 0 <= r.get("fused_opportunity_score", -1) <= 100
        and "cluster_id" in r
        for r in fused
    )

    # --- Signal explanation: each has explanation ---
    explanation_ok = all("explanation" in r for r in fused)

    # --- Board compatibility: every fused cluster_id appears in board entries ---
    board_out = build_opportunity_board(clusters, ranking_result=rank_out)
    entries = board_out.get("entries") or []
    board_cids = {e["cluster_id"] for e in entries}
    board_compat_ok = all(r["cluster_id"] in board_cids for r in fused) and len(fused) == len(entries)

    print("opportunity signal fusion OK")
    print("signal merge: OK" if merge_ok else "signal merge: FAIL")
    print("opportunity score: OK" if score_ok else "opportunity score: FAIL")
    print("signal explanation: OK" if explanation_ok else "signal explanation: FAIL")
    print("board compatibility: OK" if board_compat_ok else "board compatibility: FAIL")

    if not (merge_ok and score_ok and explanation_ok and board_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
