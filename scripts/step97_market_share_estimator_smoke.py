#!/usr/bin/env python3
"""Step 97: Market share estimator foundation – share estimation, member weighting, concentration summary, signal explanation."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.clustering import cluster_products
    from amazon_research.share import estimate_market_share

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "keyword", "source_id": "mouse", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    share_out = estimate_market_share(clusters, asin_pool=asin_pool, use_db=False)
    estimates = share_out.get("estimates") or []

    # --- Share estimation: at least one estimate per cluster ---
    share_ok = len(estimates) >= 1 and all("cluster_id" in e for e in estimates)

    # --- Member weighting: member_share_weights present and sums to ~1 per cluster ---
    weight_ok = True
    for e in estimates:
        w = e.get("member_share_weights") or {}
        if not isinstance(w, dict):
            weight_ok = False
            break
        total = sum(w.values())
        weight_ok = weight_ok and (abs(total - 1.0) < 0.01 or (len(w) == 1 and abs(total - 1.0) < 0.01))
    if not estimates:
        weight_ok = False

    # --- Concentration summary: hhi, top_share or top_asin ---
    conc_ok = all(
        "concentration_summary" in e
        and isinstance(e["concentration_summary"], dict)
        and ("hhi" in e["concentration_summary"] or "top_share" in e["concentration_summary"])
        for e in estimates
    )

    # --- Signal explanation: explanation present ---
    expl_ok = all("explanation" in e and isinstance(e.get("explanation"), str) for e in estimates)

    print("market share estimator foundation OK")
    print("share estimation: OK" if share_ok else "share estimation: FAIL")
    print("member weighting: OK" if weight_ok else "member weighting: FAIL")
    print("concentration summary: OK" if conc_ok else "concentration summary: FAIL")
    print("signal explanation: OK" if expl_ok else "signal explanation: FAIL")

    if not (share_ok and weight_ok and conc_ok and expl_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
