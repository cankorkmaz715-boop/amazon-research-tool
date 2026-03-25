#!/usr/bin/env python3
"""Step 95: Automated niche discovery – seed input, discovery workflow, cluster generation, niche output, ranking compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import run_niche_discovery
    from amazon_research.ranking import rank_cluster_opportunities

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "keyword", "source_id": "mouse", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]

    # --- Seed input: accept discovery_context + asin_pool ---
    out = run_niche_discovery(
        asin_pool=asin_pool,
        discovery_context=discovery_context,
        use_db=False,
    )
    seed_ok = "niches" in out and "summary" in out and out.get("summary", {}).get("seed_sources") == 2

    # --- Discovery workflow: pipeline runs without error ---
    workflow_ok = isinstance(out.get("niches"), list) and "summary" in out

    # --- Cluster generation: at least one niche with cluster_id ---
    niches = out.get("niches") or []
    cluster_ok = len(niches) >= 1 and all(
        n.get("cluster_id") and n.get("cluster_summary") for n in niches
    )

    # --- Niche output: niche_id, seed_source, opportunity_signals_summary ---
    niche_output_ok = all(
        "niche_id" in n
        and "seed_source" in n
        and "opportunity_signals_summary" in n
        and isinstance(n.get("opportunity_signals_summary"), dict)
        for n in niches
    )

    # --- Ranking compatibility: opportunity signals align with ranking ---
    if niches:
        from amazon_research.clustering import cluster_products
        clusters = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False).get("clusters") or []
        rank_out = rank_cluster_opportunities(clusters, use_db=False)
        ranked_ids = {r["cluster_id"] for r in rank_out.get("ranked_candidates") or []}
        niche_ids = {n["cluster_id"] for n in niches}
        ranking_compat_ok = niche_ids <= ranked_ids or len(ranked_ids) == len(niche_ids)
    else:
        ranking_compat_ok = True

    print("automated niche discovery OK")
    print("seed input: OK" if seed_ok else "seed input: FAIL")
    print("discovery workflow: OK" if workflow_ok else "discovery workflow: FAIL")
    print("cluster generation: OK" if cluster_ok else "cluster generation: FAIL")
    print("niche output: OK" if niche_output_ok else "niche output: FAIL")
    print("ranking compatibility: OK" if ranking_compat_ok else "ranking compatibility: FAIL")

    if not (seed_ok and workflow_ok and cluster_ok and niche_output_ok and ranking_compat_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
