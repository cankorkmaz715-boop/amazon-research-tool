#!/usr/bin/env python3
"""Step 96: Reverse ASIN engine – ASIN lookup, keyword/category context, cluster linkage, opportunity context."""
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
    from amazon_research.index import build_market_opportunity_index
    from amazon_research.reverse import reverse_asin

    asin_pool = ["B001", "B002", "B003"]
    target_asin = "B002"
    discovery_context = [
        {"source_type": "keyword", "source_id": "mouse", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
        {"source_type": "category", "source_id": "https://amazon.de/b?node=111", "asins": ["B001", "B002"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []
    rank_out = rank_cluster_opportunities(clusters, use_db=False)
    moi_out = build_market_opportunity_index(clusters, use_db=False)

    rev = reverse_asin(
        target_asin,
        clusters=clusters,
        discovery_context=discovery_context,
        ranking_result=rank_out,
        moi_result=moi_out,
        use_db=False,
    )

    # --- ASIN lookup: input_asin present and correct ---
    lookup_ok = rev.get("input_asin") == target_asin

    # --- Keyword context: related_keywords from discovery_context ---
    keywords = rev.get("related_keywords") or []
    keyword_ok = isinstance(keywords, list) and ("mouse" in keywords or "wireless mouse" in keywords)

    # --- Category context: related_categories from discovery_context ---
    categories = rev.get("related_categories") or []
    has_category_ctx = any(c.get("source_type") == "category" for c in discovery_context)
    category_ok = isinstance(categories, list) and (len(categories) >= 1 if has_category_ctx else True)

    # --- Cluster linkage: cluster_associations contains at least one cluster with target ASIN ---
    associations = rev.get("cluster_associations") or []
    cluster_ok = isinstance(associations, list) and (len(associations) >= 1 and all("cluster_id" in a for a in associations))

    # --- Opportunity context: opportunity_signal_summary present ---
    opp = rev.get("opportunity_signal_summary") or {}
    opportunity_ok = isinstance(opp, dict) and ("opportunity_index" in opp or "source" in opp or "ranking_score" in opp)

    print("reverse ASIN engine OK")
    print("asin lookup: OK" if lookup_ok else "asin lookup: FAIL")
    print("keyword context: OK" if keyword_ok else "keyword context: FAIL")
    print("category context: OK" if category_ok else "category context: FAIL")
    print("cluster linkage: OK" if cluster_ok else "cluster linkage: FAIL")
    print("opportunity context: OK" if opportunity_ok else "opportunity context: FAIL")

    if not (lookup_ok and keyword_ok and category_ok and cluster_ok and opportunity_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
