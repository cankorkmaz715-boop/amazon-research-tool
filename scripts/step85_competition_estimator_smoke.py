#!/usr/bin/env python3
"""Step 85: Competition estimator foundation – competition score, signal explanation, niche/ranking compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.clustering import cluster_products
    from amazon_research.niche import score_niches
    from amazon_research.ranking import rank_cluster_opportunities
    from amazon_research.competition import estimate_competition

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    comp_out = estimate_competition(clusters, asin_pool=asin_pool, use_db=False)
    estimates = comp_out.get("estimates") or []

    # --- Competition score: each estimate has competition_score and competition_level ---
    score_ok = all(
        isinstance(e.get("competition_score"), (int, float))
        and e.get("competition_level") in ("low", "medium", "high")
        and "cluster_id" in e
        for e in estimates
    )

    # --- Signal explanation: each has explanation and competition_signals ---
    explanation_ok = all(
        "explanation" in e and isinstance(e.get("competition_signals"), dict)
        for e in estimates
    )

    # --- Niche compatibility: same clusters work with score_niches ---
    niche_out = score_niches(clusters, asin_pool=asin_pool, use_db=False)
    niche_scored = niche_out.get("scored_niches") or []
    niche_compat_ok = len(niche_scored) == len(estimates) and all(
        any(est["cluster_id"] == n["cluster_id"] for n in niche_scored) for est in estimates
    )

    # --- Ranking compatibility: same clusters work with rank_cluster_opportunities ---
    rank_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    ranked = rank_out.get("ranked_candidates") or []
    ranking_compat_ok = len(ranked) == len(estimates) and all(
        any(est["cluster_id"] == r["cluster_id"] for r in ranked) for est in estimates
    )

    print("competition estimator foundation OK")
    print("competition score: OK" if score_ok else "competition score: FAIL")
    print("signal explanation: OK" if explanation_ok else "signal explanation: FAIL")
    print("niche compatibility: OK" if niche_compat_ok else "niche compatibility: FAIL")
    print("ranking compatibility: OK" if ranking_compat_ok else "ranking compatibility: FAIL")

    if not (score_ok and explanation_ok and niche_compat_ok and ranking_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
