#!/usr/bin/env python3
"""Step 98: Product launch predictor foundation – launch feasibility score, signal aggregation, explanation, niche compatibility."""
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
    from amazon_research.launch import predict_launch

    asin_pool = ["B001", "B002", "B003"]
    discovery_context = [
        {"source_type": "keyword", "source_id": "mouse", "asins": ["B001", "B002"]},
        {"source_type": "keyword", "source_id": "wireless mouse", "asins": ["B002", "B003"]},
    ]
    out = cluster_products(asin_pool, discovery_context=discovery_context, use_db=False)
    clusters = out.get("clusters") or []

    pred_out = predict_launch(clusters, asin_pool=asin_pool, use_db=False)
    predictions = pred_out.get("predictions") or []

    # --- Launch feasibility score: numeric score per cluster ---
    score_ok = all(
        isinstance(p.get("launch_feasibility_score"), (int, float))
        and 0 <= p.get("launch_feasibility_score", -1) <= 100
        and "cluster_id" in p
        for p in predictions
    )

    # --- Signal aggregation: main_supporting_signals with expected keys ---
    expected = {"demand_score", "competition_score", "trend_score", "opportunity_index"}
    signal_ok = all(
        isinstance(p.get("main_supporting_signals"), dict)
        and expected <= set(p.get("main_supporting_signals", {}))
        for p in predictions
    )

    # --- Prediction explanation: explanation string present ---
    expl_ok = all("explanation" in p and isinstance(p.get("explanation"), str) for p in predictions)

    # --- Niche compatibility: same cluster set as explorer ---
    explorer_out = explore_niches(clusters, use_db=False)
    explorer_niche_ids = {n["cluster_id"] for n in explorer_out.get("niches") or []}
    pred_ids = {p["cluster_id"] for p in predictions}
    niche_ok = pred_ids == explorer_niche_ids and len(predictions) == len(clusters)

    print("product launch predictor foundation OK")
    print("launch feasibility score: OK" if score_ok else "launch feasibility score: FAIL")
    print("signal aggregation: OK" if signal_ok else "signal aggregation: FAIL")
    print("prediction explanation: OK" if expl_ok else "prediction explanation: FAIL")
    print("niche compatibility: OK" if niche_ok else "niche compatibility: FAIL")

    if not (score_ok and signal_ok and expl_ok and niche_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
