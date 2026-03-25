#!/usr/bin/env python3
"""Step 99: Research dashboard – niche summaries, opportunity board, product analysis, filter views, launch views, dashboard readiness."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.clustering import cluster_products
    from amazon_research.dashboard import get_research_dashboard
    from amazon_research.filters import filter_opportunities

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "keyword", "source_id": "mouse", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    dashboard = get_research_dashboard(clusters, asin_pool=asin_pool, use_db=False)

    # --- Niche summaries: list from explorer ---
    niches = dashboard.get("niche_summaries") or []
    niche_ok = isinstance(niches, list) and (len(clusters) == 0 or len(niches) >= 1) and all(
        "cluster_id" in n and "opportunity_index" in n for n in niches
    )

    # --- Opportunity board integration: ranked entries ---
    entries = dashboard.get("ranked_opportunity_entries") or []
    board_ok = isinstance(entries, list) and len(entries) == len(clusters) and all(
        "cluster_id" in e and "opportunity_score" in e for e in entries
    )

    # --- Product analysis integration: analysis views ---
    analyses = dashboard.get("product_analysis_views") or []
    analysis_ok = isinstance(analyses, list) and all(
        "cluster_id" in a and "opportunity_index" in a for a in analyses
    )

    # --- Filter views: filter_compatible_views work with filter_opportunities ---
    filter_views = dashboard.get("filter_compatible_views") or []
    filter_ok = isinstance(filter_views, list)
    if filter_views:
        filtered = filter_opportunities(filter_views, min_opportunity_index=0)
        filter_ok = filter_ok and "filtered" in filtered and len(filtered.get("filtered", [])) <= len(filter_views)

    # --- Launch views: launch feasibility ---
    launch_views = dashboard.get("launch_feasibility_views") or []
    launch_ok = isinstance(launch_views, list) and all(
        "cluster_id" in l and "launch_feasibility_score" in l for l in launch_views
    )

    # --- Dashboard readiness: summary and all sections present ---
    summary = dashboard.get("summary") or {}
    readiness_ok = (
        "niche_summaries" in dashboard
        and "ranked_opportunity_entries" in dashboard
        and "product_analysis_views" in dashboard
        and "filter_compatible_views" in dashboard
        and "launch_feasibility_views" in dashboard
        and isinstance(summary, dict)
        and "clusters" in summary
    )

    print("research dashboard OK")
    print("niche summaries: OK" if niche_ok else "niche summaries: FAIL")
    print("opportunity board integration: OK" if board_ok else "opportunity board integration: FAIL")
    print("product analysis integration: OK" if analysis_ok else "product analysis integration: FAIL")
    print("filter views: OK" if filter_ok else "filter views: FAIL")
    print("launch views: OK" if launch_ok else "launch views: FAIL")
    print("dashboard readiness: OK" if readiness_ok else "dashboard readiness: FAIL")

    if not (niche_ok and board_ok and analysis_ok and filter_ok and launch_ok and readiness_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
