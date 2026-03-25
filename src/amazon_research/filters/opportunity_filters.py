"""
Opportunity filters engine. Step 93 – filter and sort niche explorer, board entries, product clusters.
Supports min/max on opportunity index, demand, competition, trend, cluster size. Lightweight, rule-based.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("filters.opportunity_filters")


def _num(item: Dict[str, Any], *keys: str, default: float = 0.0) -> float:
    """First key present in item, else default."""
    for k in keys:
        v = item.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return default


def _passes(
    item: Dict[str, Any],
    min_opportunity_index: Optional[float],
    max_opportunity_index: Optional[float],
    min_demand_score: Optional[float],
    max_demand_score: Optional[float],
    min_competition_score: Optional[float],
    max_competition_score: Optional[float],
    min_trend_score: Optional[float],
    max_trend_score: Optional[float],
    min_cluster_size: Optional[float],
    max_cluster_size: Optional[float],
) -> bool:
    opportunity = _num(item, "opportunity_index", "opportunity_score")
    demand = _num(item, "demand_score")
    competition = _num(item, "competition_score")
    trend = _num(item, "trend_score")
    size = _num(item, "cluster_size", "member_count")

    if min_opportunity_index is not None and opportunity < min_opportunity_index:
        return False
    if max_opportunity_index is not None and opportunity > max_opportunity_index:
        return False
    if min_demand_score is not None and demand < min_demand_score:
        return False
    if max_demand_score is not None and demand > max_demand_score:
        return False
    if min_competition_score is not None and competition < min_competition_score:
        return False
    if max_competition_score is not None and competition > max_competition_score:
        return False
    if min_trend_score is not None and trend < min_trend_score:
        return False
    if max_trend_score is not None and trend > max_trend_score:
        return False
    if min_cluster_size is not None and size < min_cluster_size:
        return False
    if max_cluster_size is not None and size > max_cluster_size:
        return False
    return True


def filter_opportunities(
    items: List[Dict[str, Any]],
    *,
    min_opportunity_index: Optional[float] = None,
    max_opportunity_index: Optional[float] = None,
    min_demand_score: Optional[float] = None,
    max_demand_score: Optional[float] = None,
    min_competition_score: Optional[float] = None,
    max_competition_score: Optional[float] = None,
    min_trend_score: Optional[float] = None,
    max_trend_score: Optional[float] = None,
    min_cluster_size: Optional[int] = None,
    max_cluster_size: Optional[int] = None,
    sort_by: str = "opportunity_index",
    sort_order: str = "desc",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Filter opportunity items (explorer niches, board entries, or analyzer-style items) by min/max
    thresholds. Supports opportunity_index/opportunity_score, demand_score, competition_score,
    trend_score, cluster_size/member_count. Sort by any of these or cluster_id. Returns
    { filtered, summary } with total_before, total_after, filters_applied.
    """
    filtered = [
        item for item in items
        if _passes(
            item,
            min_opportunity_index,
            max_opportunity_index,
            min_demand_score,
            max_demand_score,
            min_competition_score,
            max_competition_score,
            min_trend_score,
            max_trend_score,
            float(min_cluster_size) if min_cluster_size is not None else None,
            float(max_cluster_size) if max_cluster_size is not None else None,
        )
    ]

    # Normalize sort key
    sort_key = sort_by.strip().lower() or "opportunity_index"
    if sort_key == "opportunity_index":
        sort_key = "opportunity_index"  # use numeric; fallback to opportunity_score in key fn
    desc = (sort_order or "desc").strip().lower() == "desc"

    def key_fn(it: Dict[str, Any]) -> tuple:
        if sort_key == "opportunity_index":
            v = _num(it, "opportunity_index", "opportunity_score")
        elif sort_key == "demand_score":
            v = _num(it, "demand_score")
        elif sort_key == "competition_score":
            v = _num(it, "competition_score")
        elif sort_key == "trend_score":
            v = _num(it, "trend_score")
        elif sort_key == "cluster_size":
            v = _num(it, "cluster_size", "member_count")
        else:
            v = it.get("cluster_id") or ""
        cid = it.get("cluster_id") or ""
        return (v, cid) if isinstance(v, (int, float)) else (v, cid)

    filtered.sort(key=key_fn, reverse=desc)

    if limit is not None and limit > 0:
        filtered = filtered[:limit]

    filters_applied = {}
    if min_opportunity_index is not None:
        filters_applied["min_opportunity_index"] = min_opportunity_index
    if max_opportunity_index is not None:
        filters_applied["max_opportunity_index"] = max_opportunity_index
    if min_demand_score is not None:
        filters_applied["min_demand_score"] = min_demand_score
    if max_demand_score is not None:
        filters_applied["max_demand_score"] = max_demand_score
    if min_competition_score is not None:
        filters_applied["min_competition_score"] = min_competition_score
    if max_competition_score is not None:
        filters_applied["max_competition_score"] = max_competition_score
    if min_trend_score is not None:
        filters_applied["min_trend_score"] = min_trend_score
    if max_trend_score is not None:
        filters_applied["max_trend_score"] = max_trend_score
    if min_cluster_size is not None:
        filters_applied["min_cluster_size"] = min_cluster_size
    if max_cluster_size is not None:
        filters_applied["max_cluster_size"] = max_cluster_size

    return {
        "filtered": filtered,
        "summary": {
            "total_before": len(items),
            "total_after": len(filtered),
            "sort_by": sort_by,
            "sort_order": sort_order,
            "filters_applied": filters_applied,
        },
    }
