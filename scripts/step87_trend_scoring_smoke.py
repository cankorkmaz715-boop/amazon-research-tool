#!/usr/bin/env python3
"""Step 87: Trend scoring v2 – trend score, signal aggregation, explanation, ranking compatibility."""
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
    from amazon_research.trend import score_trends

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    trend_out = score_trends(clusters, asin_pool=asin_pool, use_db=False)
    results = trend_out.get("trend_results") or []

    # --- Trend score: each result has trend_score ---
    score_ok = all(
        isinstance(r.get("trend_score"), (int, float)) and "cluster_id" in r
        for r in results
    )

    # --- Signal aggregation: trend_signals with expected keys ---
    expected = {"member_count", "review_rising_count", "rating_rising_count", "price_falling_count"}
    agg_ok = all(
        isinstance(r.get("trend_signals"), dict) and expected <= set(r.get("trend_signals", {}))
        for r in results
    )

    # --- Signal explanation: each has explanation ---
    explanation_ok = all("explanation" in r for r in results)

    # --- Ranking compatibility: same clusters work with rank_cluster_opportunities ---
    rank_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    ranked = rank_out.get("ranked_candidates") or []
    ranking_compat_ok = len(ranked) == len(results) and all(
        any(r["cluster_id"] == x["cluster_id"] for x in ranked) for r in results
    )

    print("trend scoring v2 OK")
    print("trend score: OK" if score_ok else "trend score: FAIL")
    print("signal aggregation: OK" if agg_ok else "signal aggregation: FAIL")
    print("signal explanation: OK" if explanation_ok else "signal explanation: FAIL")
    print("ranking compatibility: OK" if ranking_compat_ok else "ranking compatibility: FAIL")

    if not (score_ok and agg_ok and explanation_ok and ranking_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
