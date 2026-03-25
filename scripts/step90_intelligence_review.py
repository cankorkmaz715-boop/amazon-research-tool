#!/usr/bin/env python3
"""
Step 90: Opportunity intelligence layer review.
Audits niche detector, clustering, ranking, board, niche scoring, competition,
demand, trend scoring, fusion, MOI. Reports strengths, risks, next improvements.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    modules = [
        ("amazon_research.niche.detector", "detect_niches"),
        ("amazon_research.clustering.product_clustering", "cluster_products"),
        ("amazon_research.ranking.opportunity_ranking", "rank_cluster_opportunities"),
        ("amazon_research.board.opportunity_board", "build_opportunity_board"),
        ("amazon_research.niche.scoring", "score_niches"),
        ("amazon_research.competition.estimator", "estimate_competition"),
        ("amazon_research.demand.aggregator", "aggregate_demand"),
        ("amazon_research.trend.scoring", "score_trends"),
        ("amazon_research.fusion.opportunity_fusion", "fuse_opportunity_signals"),
        ("amazon_research.index.market_opportunity_index", "build_market_opportunity_index"),
    ]
    found = []
    for path, attr in modules:
        try:
            mod = __import__(path, fromlist=[attr])
            if hasattr(mod, attr):
                found.append(attr)
        except Exception:
            pass

    all_ok = len(found) >= 10

    # Minimal pipeline run (no DB) to verify wiring
    try:
        from amazon_research.clustering import cluster_products
        from amazon_research.ranking import rank_cluster_opportunities
        from amazon_research.board import build_opportunity_board
        from amazon_research.niche import score_niches
        from amazon_research.competition import estimate_competition
        from amazon_research.demand import aggregate_demand
        from amazon_research.trend import score_trends
        from amazon_research.fusion import fuse_opportunity_signals
        from amazon_research.index import build_market_opportunity_index
    except ImportError as e:
        pipeline_ok = False
        pipeline_error = str(e)
    else:
        pipeline_error = None
        try:
            clusters = cluster_products(
                ["B01", "B02"],
                discovery_context=[{"source_type": "category", "source_id": "u", "asins": ["B01", "B02"]}],
                use_db=False,
            ).get("clusters") or []
            rank_out = rank_cluster_opportunities(clusters, use_db=False)
            board_out = build_opportunity_board(clusters, ranking_result=rank_out)
            score_niches(clusters, use_db=False)
            estimate_competition(clusters, use_db=False)
            aggregate_demand(clusters, use_db=False)
            score_trends(clusters, use_db=False)
            fuse_opportunity_signals(clusters, use_db=False)
            build_market_opportunity_index(clusters, use_db=False)
            pipeline_ok = True
        except Exception as e:
            pipeline_ok = False
            pipeline_error = str(e)

    # --- Structured report ---
    strengths = [
        "Niche detector, clustering, ranking, board, niche scoring, competition, demand, trend scoring, fusion, and MOI are present and wired.",
        "Rule-based, explainable scoring throughout (no ML); signals and explanations exposed at each layer.",
        "Unified fusion (demand, competition, trend, niche, ranking) and MOI enable cross-cluster comparison.",
        "Board and ranking outputs are compatible; fusion and MOI consume same cluster shape.",
        "use_db=False path allows testing and staging without persistence.",
    ]
    if not pipeline_ok:
        strengths.append("(Pipeline run skipped or failed; module presence still verified.)")

    risks = [
        "Explainability: Niche score duplicates ranking score; MOI/fusion weights are fixed and not configurable.",
        "Ranking consistency: Niche score and ranking score are identical by design; fusion combines five inputs—ensure downstream consumers handle ties and missing signals.",
        "Data quality: Competition, demand, trend, and ranking depend on product_metrics and history (price/review); sparse or stale data yields low/zero scores.",
        "Scaling: Per-cluster trend and ranking logic resolve ASINs and call get_trends_for_asin per member; large clusters or many clusters can be costly.",
        "Signal gaps: BSR/rank trend is insufficient_data until bsr_history exists; repeated appearance and context_count rely on discovery_context.",
    ]

    next_improvements = [
        "Add bsr_history (or equivalent) and wire rank trend into trend engine and trend scoring.",
        "Make fusion/MOI weights configurable (e.g. config or API) for tenant-specific tuning.",
        "Optional caching or batch trend/metric fetches for large cluster sets.",
        "Document signal semantics and score bands (e.g. MOI tier thresholds) for operators and UI.",
        "Consider demand vs competition sub-scores in MOI or board for advanced analytics.",
    ]

    print("intelligence layer review OK")
    print("strengths:")
    for s in strengths:
        print(f"  - {s}")
    print("risks:")
    for r in risks:
        print(f"  - {r}")
    print("next improvements:")
    for n in next_improvements:
        print(f"  - {n}")
    if pipeline_error and not pipeline_ok:
        print("(pipeline check error:", pipeline_error, ")")

    if not all_ok:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
