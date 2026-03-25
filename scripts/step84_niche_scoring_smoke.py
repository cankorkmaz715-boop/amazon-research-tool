#!/usr/bin/env python3
"""Step 84: Niche scoring v2 – niche score, signal explanation, ranking compatibility, board compatibility."""
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
    from amazon_research.niche import score_niches

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    # --- Niche score: each scored niche has numeric niche_score ---
    scoring_out = score_niches(clusters, asin_pool=asin_pool, use_db=False)
    scored = scoring_out.get("scored_niches") or []
    niche_ok = all(
        isinstance(s.get("niche_score"), (int, float)) and "cluster_id" in s
        for s in scored
    )

    # --- Signal explanation: each has explanation and contributing_signals ---
    explanation_ok = all(
        "explanation" in s and isinstance(s.get("contributing_signals"), dict)
        for s in scored
    )

    # --- Ranking compatibility: niche_score matches opportunity ranking score for same clusters ---
    rank_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    ranked = rank_out.get("ranked_candidates") or []
    rank_by_id = {r["cluster_id"]: r["score"] for r in ranked}
    ranking_compat_ok = all(
        s.get("niche_score") == rank_by_id.get(s.get("cluster_id"))
        for s in scored
    )

    # --- Board compatibility: board entries can be augmented with niche_score from scored_niches ---
    board_out = build_opportunity_board(clusters, ranking_result=rank_out)
    entries = board_out.get("entries") or []
    scored_by_id = {s["cluster_id"]: s["niche_score"] for s in scored}
    board_compat_ok = all(
        e.get("cluster_id") in scored_by_id and e.get("opportunity_score") == scored_by_id.get(e.get("cluster_id"))
        for e in entries
    )

    print("niche scoring v2 OK")
    print("niche score: OK" if niche_ok else "niche score: FAIL")
    print("signal explanation: OK" if explanation_ok else "signal explanation: FAIL")
    print("ranking compatibility: OK" if ranking_compat_ok else "ranking compatibility: FAIL")
    print("board compatibility: OK" if board_compat_ok else "board compatibility: FAIL")

    if not (niche_ok and explanation_ok and ranking_compat_ok and board_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
