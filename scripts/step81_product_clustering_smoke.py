#!/usr/bin/env python3
"""Step 81: Product clustering foundation – cluster generation, member grouping, output structure, signals."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.clustering import cluster_products

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
    summary = out.get("summary") or {}

    # --- Cluster generation: at least one cluster from niche ---
    gen_ok = isinstance(clusters, list) and len(clusters) >= 1

    # --- Member grouping: each cluster has member_asins list ---
    member_ok = all(
        isinstance(c, dict) and "member_asins" in c and isinstance(c["member_asins"], list)
        for c in clusters
    )

    # --- Cluster output structure: cluster_id, member_asins, label, rationale ---
    structure_ok = all(
        "cluster_id" in c and "member_asins" in c and "label" in c and "rationale" in c
        for c in clusters
    )

    # --- Clustering signals: rationale contains signals ---
    signals_ok = all(
        isinstance(c.get("rationale"), dict) and "signals" in c.get("rationale", {})
        for c in clusters
    )

    print("product clustering foundation OK")
    print("cluster generation: OK" if gen_ok else "cluster generation: FAIL")
    print("member grouping: OK" if member_ok else "member grouping: FAIL")
    print("cluster output structure: OK" if structure_ok else "cluster output structure: FAIL")
    print("clustering signals: OK" if signals_ok else "clustering signals: FAIL")

    if not (gen_ok and member_ok and structure_ok and signals_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
