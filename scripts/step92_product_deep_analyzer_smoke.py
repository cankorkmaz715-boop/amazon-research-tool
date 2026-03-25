#!/usr/bin/env python3
"""Step 92: Product deep analyzer – signal aggregation, analysis output, explainer signals, board compatibility."""
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
    from amazon_research.analyzer import deep_analyze, deep_analyze_batch

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    # Analyze first cluster
    single = deep_analyze(clusters[0] if clusters else {"cluster_id": "c1", "member_asins": ["B001"], "label": "L1"}, use_db=False)
    batch = deep_analyze_batch([clusters[0], clusters[1]] if len(clusters) >= 2 else clusters, use_db=False)
    analyses = batch.get("analyses") or []

    # --- Signal aggregation: demand, competition, trend, niche, opportunity from MOI ---
    agg_ok = (
        "opportunity_index" in single
        and "demand_score" in single
        and "competition_score" in single
        and "trend_score" in single
        and "niche_score" in single
    )

    # --- Analysis output: product_id, cluster_id, key_signals_summary ---
    output_ok = (
        "product_id" in single
        and "cluster_id" in single
        and "key_signals_summary" in single
        and isinstance(single.get("key_signals_summary"), str)
    )

    # --- Explainer signals: contributing_signals present ---
    explainer_ok = (
        "contributing_signals" in single
        and isinstance(single.get("contributing_signals"), dict)
    )

    # --- Board compatibility: cluster_id from analyzer matches board entries ---
    rank_out = rank_cluster_opportunities(clusters, use_db=False)
    board_out = build_opportunity_board(clusters, ranking_result=rank_out)
    board_cids = {e["cluster_id"] for e in board_out.get("entries") or []}
    board_compat_ok = single.get("cluster_id") in board_cids or len(clusters) == 0
    if analyses:
        board_compat_ok = board_compat_ok and all(a.get("cluster_id") in board_cids for a in analyses)

    print("product deep analyzer OK")
    print("signal aggregation: OK" if agg_ok else "signal aggregation: FAIL")
    print("analysis output: OK" if output_ok else "analysis output: FAIL")
    print("explainer signals: OK" if explainer_ok else "explainer signals: FAIL")
    print("board compatibility: OK" if board_compat_ok else "board compatibility: FAIL")

    if not (agg_ok and output_ok and explainer_ok and board_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
