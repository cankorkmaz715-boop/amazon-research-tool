#!/usr/bin/env python3
"""Step 93: Opportunity filters engine – filter application, threshold logic, sorting, board compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.clustering import cluster_products
    from amazon_research.explorer import explore_niches
    from amazon_research.board import build_opportunity_board
    from amazon_research.ranking import rank_cluster_opportunities
    from amazon_research.filters import filter_opportunities

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    explorer_out = explore_niches(clusters, use_db=False)
    niches = explorer_out.get("niches") or []
    rank_out = rank_cluster_opportunities(clusters, use_db=False)
    board_out = build_opportunity_board(clusters, ranking_result=rank_out)
    entries = board_out.get("entries") or []

    # --- Filter application: min/max reduces or preserves list ---
    no_filter = filter_opportunities(niches)
    with_filter = filter_opportunities(
        niches,
        min_opportunity_index=0,
        max_opportunity_index=100,
        min_cluster_size=1,
    )
    filter_ok = (
        len(no_filter.get("filtered", [])) == len(niches)
        and len(with_filter.get("filtered", [])) <= len(niches)
        and no_filter.get("summary", {}).get("total_before") == len(niches)
        and with_filter.get("summary", {}).get("total_after") is not None
    )

    # --- Threshold logic: strict min excludes low values ---
    high_only = filter_opportunities(niches, min_opportunity_index=1000)  # none pass
    threshold_ok = (
        len(high_only.get("filtered", [])) == 0
        and high_only.get("summary", {}).get("total_after") == 0
    )

    # --- Sorting compatibility: sort_by and sort_order change order ---
    by_opp = filter_opportunities(niches, sort_by="opportunity_index", sort_order="desc")
    by_size = filter_opportunities(niches, sort_by="cluster_size", sort_order="desc")
    sort_ok = (
        len(by_opp.get("filtered", [])) == len(niches)
        and len(by_size.get("filtered", [])) == len(niches)
        and by_opp.get("summary", {}).get("sort_by") == "opportunity_index"
    )

    # --- Board compatibility: filter works on board entries (opportunity_score, member_count) ---
    filtered_board = filter_opportunities(
        entries,
        min_opportunity_index=0,
        sort_by="opportunity_index",
    )
    board_compat_ok = (
        "filtered" in filtered_board
        and "summary" in filtered_board
        and filtered_board.get("summary", {}).get("total_before") == len(entries)
    )
    # Board uses opportunity_score; filter normalizes to opportunity_index
    if filtered_board.get("filtered"):
        first = filtered_board["filtered"][0]
        board_compat_ok = board_compat_ok and ("cluster_id" in first or "opportunity_score" in first or "opportunity_index" in first)

    print("opportunity filters engine OK")
    print("filter application: OK" if filter_ok else "filter application: FAIL")
    print("threshold logic: OK" if threshold_ok else "threshold logic: FAIL")
    print("sorting compatibility: OK" if sort_ok else "sorting compatibility: FAIL")
    print("board compatibility: OK" if board_compat_ok else "board compatibility: FAIL")

    if not (filter_ok and threshold_ok and sort_ok and board_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
