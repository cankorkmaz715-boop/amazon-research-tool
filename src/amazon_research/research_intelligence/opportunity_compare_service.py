"""
Steps 243–245: Opportunity comparison engine. Max 5 items; workspace-scoped.
"""
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("research_intelligence.compare")

MAX_COMPARE = 5


def compare_opportunities(workspace_id: int, opportunity_ids: List[int]) -> Dict[str, Any]:
    """Return compared_items, score_comparison, risk_comparison, ranking_comparison. Max 5 ids."""
    ids = [x for x in opportunity_ids if isinstance(x, (int, float)) and int(x) > 0][:MAX_COMPARE]
    ids = list(dict.fromkeys([int(x) for x in ids]))
    compared_items: List[Dict[str, Any]] = []
    score_comparison: List[Dict[str, Any]] = []
    risk_comparison: List[Dict[str, Any]] = []
    ranking_comparison: List[Dict[str, Any]] = []
    try:
        from amazon_research.opportunity_detail import get_opportunity_detail
        for oid in ids:
            detail = get_opportunity_detail(workspace_id, oid)
            if not detail:
                continue
            compared_items.append({
                "opportunity_id": oid,
                "title": detail.get("title") or "",
                "score": detail.get("score"),
                "priority": detail.get("priority") or "",
                "ranking_position": detail.get("ranking_position"),
                "risk_indicator": detail.get("risk_indicator") or "",
            })
            score_comparison.append({"opportunity_id": oid, "score": detail.get("score")})
            risk_comparison.append({"opportunity_id": oid, "risk_indicator": detail.get("risk_indicator") or "low"})
            ranking_comparison.append({"opportunity_id": oid, "ranking_position": detail.get("ranking_position")})
    except Exception as e:
        logger.warning("compare_opportunities failed workspace_id=%s: %s", workspace_id, e)
    return {
        "compared_items": compared_items,
        "score_comparison": score_comparison,
        "risk_comparison": risk_comparison,
        "ranking_comparison": ranking_comparison,
    }
