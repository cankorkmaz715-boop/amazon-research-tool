#!/usr/bin/env python3
"""Step 82: Opportunity ranking v2 – cluster scoring, signal aggregation, ranking output, explainable signals."""
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

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(
        asin_pool,
        discovery_context=discovery_context,
        use_db=False,
    )
    clusters = out.get("clusters") or []

    ranked_out = rank_cluster_opportunities(clusters, asin_pool=asin_pool, use_db=False)
    candidates = ranked_out.get("ranked_candidates") or []
    summary = ranked_out.get("summary") or {}

    # --- Cluster scoring: each candidate has a numeric score ---
    scoring_ok = all(
        isinstance(c.get("score"), (int, float)) and c.get("cluster_id")
        for c in candidates
    )

    # --- Signal aggregation: signals_used present with expected keys ---
    expected_keys = {"cluster_size", "has_niche_context"}
    signals_ok = all(
        isinstance(c.get("signals_used"), dict) and expected_keys <= set(c.get("signals_used", {}))
        for c in candidates
    )

    # --- Ranking output: ranked list, descending score ---
    scores = [c.get("score", 0) for c in candidates]
    ranking_ok = (
        isinstance(candidates, list)
        and len(candidates) == len(clusters)
        and scores == sorted(scores, reverse=True)
    )

    # --- Explainable signals: explanation and signals_used ---
    explain_ok = all(
        "explanation" in c and isinstance(c.get("signals_used"), dict)
        for c in candidates
    )

    print("opportunity ranking v2 OK")
    print("cluster scoring: OK" if scoring_ok else "cluster scoring: FAIL")
    print("signal aggregation: OK" if signals_ok else "signal aggregation: FAIL")
    print("ranking output: OK" if ranking_ok else "ranking output: FAIL")
    print("explainable signals: OK" if explain_ok else "explainable signals: FAIL")

    if not (scoring_ok and signals_ok and ranking_ok and explain_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
