#!/usr/bin/env python3
"""Step 91: Niche explorer foundation – niche listing, cluster mapping, signal exposure, ranking compatibility."""
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
    from amazon_research.explorer import explore_niches

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    explorer_out = explore_niches(clusters, asin_pool=asin_pool, use_db=False)
    niches = explorer_out.get("niches") or []

    # --- Niche listing: multiple niches in ranked order ---
    listing_ok = (
        isinstance(niches, list)
        and len(niches) >= 1
        and all(
            "niche_id" in n and "cluster_id" in n and "label" in n
            for n in niches
        )
    )

    # --- Cluster mapping: niche_id and cluster_id align with clusters ---
    cluster_ids = {c["cluster_id"] for c in clusters}
    mapping_ok = all(
        n["cluster_id"] in cluster_ids and n["niche_id"] == n["cluster_id"]
        for n in niches
    )

    # --- Signal exposure: opportunity_index, demand_score, competition_score, cluster_size ---
    signal_ok = all(
        "opportunity_index" in n
        and "demand_score" in n
        and "competition_score" in n
        and "cluster_size" in n
        and isinstance(n.get("cluster_size"), int)
        for n in niches
    )

    # --- Ranking compatibility: same cluster set as board, ordered by opportunity ---
    rank_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    board_out = build_opportunity_board(clusters, ranking_result=rank_out)
    board_cids = {e["cluster_id"] for e in board_out.get("entries") or []}
    explorer_cids = {n["cluster_id"] for n in niches}
    ranking_compat_ok = explorer_cids == board_cids and len(niches) == len(clusters)
    if len(niches) >= 2:
        ranking_compat_ok = ranking_compat_ok and niches == sorted(
            niches, key=lambda x: (-x["opportunity_index"], x["cluster_id"])
        )

    print("niche explorer foundation OK")
    print("niche listing: OK" if listing_ok else "niche listing: FAIL")
    print("cluster mapping: OK" if mapping_ok else "cluster mapping: FAIL")
    print("signal exposure: OK" if signal_ok else "signal exposure: FAIL")
    print("ranking compatibility: OK" if ranking_compat_ok else "ranking compatibility: FAIL")

    if not (listing_ok and mapping_ok and signal_ok and ranking_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
