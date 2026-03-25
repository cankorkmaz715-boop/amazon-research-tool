"""
Step 188: Opportunity ranking engine – prioritize discovered opportunities using five signals.
Uses demand_score, competition_score, trend_score, price_stability, listing_density to produce opportunity_score.
Stores in opportunity_rankings; historical score blending for ranking stability.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_ranking_engine")

# Weights for composite opportunity_score (0–100). Competition reduces opportunity.
WEIGHT_DEMAND = 0.35
WEIGHT_COMPETITION = -0.25  # subtract
WEIGHT_TREND = 0.20
WEIGHT_PRICE_STABILITY = 0.10
WEIGHT_LISTING_DENSITY = 0.10
# Blending with previous score for stability (alpha = current weight)
BLEND_ALPHA = 0.7  # final = alpha * current + (1-alpha) * previous


def _f(v: Optional[float]) -> float:
    if v is None:
        return 0.0
    try:
        return max(0.0, min(100.0, float(v)))
    except (TypeError, ValueError):
        return 0.0


def compute_opportunity_score(
    demand_score: Optional[float] = None,
    competition_score: Optional[float] = None,
    trend_score: Optional[float] = None,
    price_stability: Optional[float] = None,
    listing_density: Optional[float] = None,
) -> float:
    """
    Compute raw opportunity_score from five signals. 0–100.
    Demand and trend contribute positively; competition contributes negatively; stability and density add.
    """
    d = _f(demand_score)
    c = _f(competition_score)
    t = _f(trend_score)
    p = _f(price_stability)
    l = _f(listing_density)
    raw = (
        WEIGHT_DEMAND * d
        + WEIGHT_COMPETITION * c
        + WEIGHT_TREND * t
        + WEIGHT_PRICE_STABILITY * p
        + WEIGHT_LISTING_DENSITY * l
    )
    # Map to 0–100: raw can be negative; shift and clamp
    raw = raw + 25.0  # competition max 25 negative, so shift
    return round(min(100.0, max(0.0, raw)), 2)


def get_previous_score(opportunity_ref: str) -> Optional[float]:
    """Return the most recent opportunity_score for this ref from opportunity_rankings, or None."""
    try:
        from amazon_research.db.opportunity_rankings import get_latest_ranking
        row = get_latest_ranking(opportunity_ref)
        if row and row.get("opportunity_score") is not None:
            return float(row["opportunity_score"])
    except Exception as e:
        logger.debug("get_previous_score: %s", e)
    return None


def blend_with_history(
    current_score: float,
    previous_score: Optional[float],
    alpha: float = BLEND_ALPHA,
) -> float:
    """Blend current score with previous for stability. If no previous, return current."""
    if previous_score is None:
        return round(current_score, 2)
    blended = alpha * current_score + (1.0 - alpha) * float(previous_score)
    return round(min(100.0, max(0.0, blended)), 2)


def rank_opportunities(
    scored_list: List[Dict[str, Any]],
    score_key: str = "opportunity_score",
) -> List[Dict[str, Any]]:
    """Sort by score descending and assign rank 1, 2, 3, ..."""
    sorted_list = sorted(
        scored_list,
        key=lambda x: (x.get(score_key) or 0),
        reverse=True,
    )
    for i, item in enumerate(sorted_list, start=1):
        item["rank"] = i
    return sorted_list


def compute_and_blend(
    opportunity_ref: str,
    demand_score: Optional[float] = None,
    competition_score: Optional[float] = None,
    trend_score: Optional[float] = None,
    price_stability: Optional[float] = None,
    listing_density: Optional[float] = None,
    use_blending: bool = True,
) -> Dict[str, Any]:
    """
    Compute raw opportunity_score, optionally blend with previous, return dict with opportunity_score, previous_score, blended.
    """
    raw = compute_opportunity_score(
        demand_score=demand_score,
        competition_score=competition_score,
        trend_score=trend_score,
        price_stability=price_stability,
        listing_density=listing_density,
    )
    previous = get_previous_score(opportunity_ref) if use_blending else None
    final = blend_with_history(raw, previous) if use_blending else raw
    return {
        "opportunity_ref": opportunity_ref,
        "raw_score": raw,
        "previous_score": previous,
        "opportunity_score": final,
        "demand_score": demand_score,
        "competition_score": competition_score,
        "trend_score": trend_score,
        "price_stability": price_stability,
        "listing_density": listing_density,
    }


def run_ranking(
    opportunity_refs: Optional[List[str]] = None,
    limit: int = 50,
    use_blending: bool = True,
    persist: bool = True,
) -> Dict[str, Any]:
    """
    Load opportunities (from refs or opportunity_memory + signal_results), compute scores with blending, assign ranks, persist.
    Returns: rankings (list of dicts with opportunity_ref, opportunity_score, rank, ...), stored_count.
    """
    refs = opportunity_refs
    if refs is None:
        try:
            from amazon_research.db import list_opportunity_memory
            from amazon_research.db.signal_results import get_signal_result_latest
            mem_list = list_opportunity_memory(limit=limit)
            refs = [m.get("opportunity_ref") for m in mem_list if m.get("opportunity_ref")]
        except Exception as e:
            logger.debug("run_ranking list_opportunity_memory: %s", e)
            refs = []

    scored: List[Dict[str, Any]] = []
    for ref in (refs or []):
        ref = (ref or "").strip()
        if not ref:
            continue
        signals = None
        try:
            from amazon_research.db.signal_results import get_signal_result_latest
            row = get_signal_result_latest(ref)
            if row:
                signals = row
        except Exception:
            pass
        d = signals.get("demand_estimate") if signals else None
        c = signals.get("competition_level") if signals else None
        t = signals.get("trend_signal") if signals else None
        p = signals.get("price_stability") if signals else None
        l = signals.get("listing_density") if signals else None
        out = compute_and_blend(
            ref,
            demand_score=d,
            competition_score=c,
            trend_score=t,
            price_stability=p,
            listing_density=l,
            use_blending=use_blending,
        )
        scored.append(out)

    ranked = rank_opportunities(scored, score_key="opportunity_score")

    stored_count = 0
    if persist and ranked:
        try:
            from amazon_research.db.opportunity_rankings import insert_ranking
            for r in ranked:
                rid = insert_ranking(
                    opportunity_ref=r["opportunity_ref"],
                    opportunity_score=r["opportunity_score"],
                    rank=r.get("rank"),
                    demand_score=r.get("demand_score"),
                    competition_score=r.get("competition_score"),
                    trend_score=r.get("trend_score"),
                    price_stability=r.get("price_stability"),
                    listing_density=r.get("listing_density"),
                    previous_score=r.get("previous_score"),
                    score_history=[{"score": r["opportunity_score"], "raw": r.get("raw_score"), "previous": r.get("previous_score")}],
                )
                if rid is not None:
                    stored_count += 1
        except Exception as e:
            logger.debug("run_ranking insert_ranking: %s", e)

    return {"rankings": ranked, "stored_count": stored_count}
