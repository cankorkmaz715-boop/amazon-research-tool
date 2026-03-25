"""
Research dashboard integration layer. Step 99 – combine niche explorer, board, analyzer, filters, reverse ASIN, launch predictor.
Backend-first, dashboard-ready outputs. No frontend rewrite.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("dashboard.research_dashboard")


def get_research_dashboard(
    clusters: List[Dict[str, Any]],
    asin_pool: Optional[List[str]] = None,
    use_db: bool = True,
    *,
    limit_niches: Optional[int] = None,
    limit_analyses: Optional[int] = 5,
) -> Dict[str, Any]:
    """
    Build a dashboard-ready payload combining niche explorer, opportunity board, deep analyzer,
    filter-compatible views, and launch predictor. Returns a single structured object for UI consumption.
    """
    if not clusters:
        return {
            "niche_summaries": [],
            "ranked_opportunity_entries": [],
            "product_analysis_views": [],
            "filter_compatible_views": [],
            "launch_feasibility_views": [],
            "summary": {"clusters": 0},
        }

    pool = asin_pool or []
    out: Dict[str, Any] = {}

    # --- Niche summaries (explorer) ---
    try:
        from amazon_research.explorer import explore_niches
        explorer = explore_niches(
            clusters,
            asin_pool=pool or None,
            use_db=use_db,
            limit=limit_niches,
        )
        out["niche_summaries"] = explorer.get("niches") or []
    except Exception as e:
        logger.debug("dashboard: explore_niches: %s", e)
        out["niche_summaries"] = []

    # --- Ranked opportunity entries (board) ---
    try:
        from amazon_research.board import build_opportunity_board
        board = build_opportunity_board(
            clusters,
            asin_pool=pool or None,
            use_db=use_db,
        )
        out["ranked_opportunity_entries"] = board.get("entries") or []
    except Exception as e:
        logger.debug("dashboard: build_opportunity_board: %s", e)
        out["ranked_opportunity_entries"] = []

    # --- Product analysis views (deep analyzer on clusters) ---
    try:
        from amazon_research.analyzer import deep_analyze_batch
        to_analyze = clusters[: limit_analyses] if limit_analyses else clusters
        analyses = deep_analyze_batch(
            to_analyze,
            asin_pool=pool or None,
            use_db=use_db,
        )
        out["product_analysis_views"] = analyses.get("analyses") or []
    except Exception as e:
        logger.debug("dashboard: deep_analyze_batch: %s", e)
        out["product_analysis_views"] = []

    # --- Filter-compatible views (same shape as filter_opportunities input) ---
    out["filter_compatible_views"] = out.get("niche_summaries", []) or out.get("ranked_opportunity_entries", [])

    # --- Launch feasibility views (predictor) ---
    try:
        from amazon_research.launch import predict_launch
        launch = predict_launch(
            clusters,
            asin_pool=pool or None,
            use_db=use_db,
        )
        out["launch_feasibility_views"] = launch.get("predictions") or []
    except Exception as e:
        logger.debug("dashboard: predict_launch: %s", e)
        out["launch_feasibility_views"] = []

    out["summary"] = {
        "clusters": len(clusters),
        "niches": len(out.get("niche_summaries", [])),
        "opportunity_entries": len(out.get("ranked_opportunity_entries", [])),
        "analysis_views": len(out.get("product_analysis_views", [])),
        "launch_views": len(out.get("launch_feasibility_views", [])),
    }
    return out
