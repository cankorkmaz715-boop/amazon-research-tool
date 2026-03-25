"""
Step 150: Copilot research strategy advisor – analyze research outputs and recommend high-level research directions.
Uses opportunity scores, confidence, lifecycle, trend, comparison outputs, insight summaries.
Rule-based, explainable. Integrates with recommendation engine, insight summarizer, comparative mode.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.research_strategy_advisor")

# Direction type constants
DIRECTION_PROMISING_NICHE = "promising_niche"
DIRECTION_MARKET_INVESTIGATE = "market_to_investigate"
DIRECTION_CLUSTER_DEEPER = "cluster_deeper_analysis"
DIRECTION_AVOID = "direction_to_avoid"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_research_strategy(
    *,
    workspace_id: Optional[int] = None,
    comparison_output: Optional[Dict[str, Any]] = None,
    insight_summaries: Optional[List[Dict[str, Any]]] = None,
    limit_recommendations: int = 20,
    limit_confidence: int = 15,
    limit_lifecycle: int = 15,
) -> Dict[str, Any]:
    """
    Analyze research outputs and recommend high-level research directions.
    Returns: strategy_id, analyzed_research_context, recommended_research_directions,
    risk_notes, reasoning_summary, timestamp.
    """
    strategy_id = f"strategy-{uuid.uuid4().hex[:12]}"
    analyzed: Dict[str, Any] = {
        "opportunity_count": 0,
        "confidence_summary": {},
        "lifecycle_summary": {},
        "comparison_summary": None,
        "insight_count": 0,
    }
    recommended_directions: List[Dict[str, Any]] = []
    risk_notes: List[str] = []
    reasoning_parts: List[str] = []

    # 1) Gather recommendations (opportunity scores, types)
    recos: List[Dict[str, Any]] = []
    try:
        from amazon_research.discovery import get_recommendations
        recos = get_recommendations(workspace_id=workspace_id, limit=limit_recommendations)
    except Exception as e:
        logger.debug("get_research_strategy get_recommendations: %s", e)
    analyzed["opportunity_count"] = len(recos)

    # 2) Confidence and lifecycle signals
    try:
        from amazon_research.discovery import list_opportunities_with_confidence, list_opportunities_with_lifecycle
        with_conf = list_opportunities_with_confidence(limit=limit_confidence, workspace_id=workspace_id)
        with_life = list_opportunities_with_lifecycle(limit=limit_lifecycle, workspace_id=workspace_id)
        low_conf = sum(1 for c in with_conf if (c.get("confidence_label") or "").lower() == "low")
        high_conf = sum(1 for c in with_conf if (c.get("confidence_label") or "").lower() == "high")
        analyzed["confidence_summary"] = {"total": len(with_conf), "low": low_conf, "high": high_conf}
        weakening = sum(1 for l in with_life if (l.get("lifecycle_state") or "").lower() in ("weakening", "fading"))
        rising = sum(1 for l in with_life if (l.get("lifecycle_state") or "").lower() in ("rising", "stable", "new"))
        analyzed["lifecycle_summary"] = {"total": len(with_life), "weakening_or_fading": weakening, "rising_stable_new": rising}
        for c in with_conf:
            if (c.get("confidence_label") or "").lower() == "low":
                ref = c.get("opportunity_id") or "unknown"
                risk_notes.append(f"Low confidence for opportunity {ref}.")
        for l in with_life:
            if (l.get("lifecycle_state") or "").lower() in ("weakening", "fading"):
                ref = l.get("opportunity_id") or "unknown"
                risk_notes.append(f"Lifecycle weakening/fading for {ref}.")
    except Exception as e:
        logger.debug("get_research_strategy confidence/lifecycle: %s", e)

    # 3) Comparison output (if provided)
    if comparison_output and isinstance(comparison_output, dict):
        analyzed["comparison_summary"] = {
            "comparison_id": comparison_output.get("comparison_id"),
            "targets_count": len(comparison_output.get("targets_compared") or []),
            "suggested_best": comparison_output.get("suggested_best_candidate"),
        }
        best = comparison_output.get("suggested_best_candidate") or {}
        if best.get("label"):
            label = best.get("label")
            rec_type = DIRECTION_MARKET_INVESTIGATE if isinstance(label, str) and ("market" in label.lower() or label.upper() in ("US", "UK", "DE")) else DIRECTION_PROMISING_NICHE
            recommended_directions.append({
                "direction_type": rec_type,
                "target": label,
                "rationale": best.get("rationale") or "Suggested best from comparative research.",
            })

    # 4) Insight summaries (if provided)
    if insight_summaries and isinstance(insight_summaries, list):
        analyzed["insight_count"] = len(insight_summaries)
        for s in insight_summaries:
            if (s.get("key_insights") or []) and len(recommended_directions) < 10:
                target = s.get("target_research_request_id") or s.get("target_execution_id") or "research"
                recommended_directions.append({
                    "direction_type": DIRECTION_CLUSTER_DEEPER,
                    "target": target,
                    "rationale": f"Insight summary has {len(s.get('key_insights', []))} key insight(s); worth deeper analysis.",
                })

    # 5) Recommendations -> promising niches, clusters, directions to avoid
    for r in recos[:15]:
        entity = r.get("target_entity") or {}
        ref = entity.get("ref") or entity.get("id") or ""
        rec_type = (r.get("recommendation_type") or "").strip()
        priority = r.get("priority_score") or 0
        expl = (r.get("explanation") or "").strip()
        if not ref:
            continue
        if priority >= 55 and rec_type in ("high_opportunity", "lifecycle_rising", "trend_positive"):
            recommended_directions.append({
                "direction_type": DIRECTION_PROMISING_NICHE,
                "target": ref,
                "rationale": expl or f"High priority ({priority:.0f}); {rec_type}.",
            })
        elif priority >= 45:
            recommended_directions.append({
                "direction_type": DIRECTION_CLUSTER_DEEPER,
                "target": ref,
                "rationale": expl or f"Worth deeper analysis; priority {priority:.0f}.",
            })
    # Directions to avoid: from risk_notes (low confidence, weakening)
    for r in risk_notes[:5]:
        target = "unknown"
        if r and " for " in r:
            parts = r.split(" for ", 1)
            if len(parts) > 1:
                target = parts[-1].rstrip(".").strip()
        elif r:
            target = r.split()[-1].rstrip(".") if r.split() else "unknown"
        recommended_directions.append({
            "direction_type": DIRECTION_AVOID,
            "target": target,
            "rationale": r,
        })

    # 6) Deduplicate and cap directions (avoid duplicates by target)
    seen_targets: set = set()
    unique_directions: List[Dict[str, Any]] = []
    for d in recommended_directions:
        t = (d.get("target") or "", d.get("direction_type") or "")
        if t in seen_targets:
            continue
        seen_targets.add(t)
        unique_directions.append(d)
    recommended_directions = unique_directions[:20]

    # 7) Reasoning summary
    reasoning_parts.append(f"Analyzed {analyzed['opportunity_count']} recommendation(s).")
    if analyzed.get("confidence_summary"):
        cs = analyzed["confidence_summary"]
        reasoning_parts.append(f"Confidence: {cs.get('total', 0)} opportunities ({cs.get('high', 0)} high, {cs.get('low', 0)} low).")
    if analyzed.get("lifecycle_summary"):
        ls = analyzed["lifecycle_summary"]
        reasoning_parts.append(f"Lifecycle: {ls.get('rising_stable_new', 0)} rising/stable/new, {ls.get('weakening_or_fading', 0)} weakening/fading.")
    if comparison_output:
        reasoning_parts.append("Comparative research output included; best candidate suggested.")
    reasoning_parts.append(f"Suggested {len([d for d in recommended_directions if d.get('direction_type') != DIRECTION_AVOID])} direction(s) to explore and {len([d for d in recommended_directions if d.get('direction_type') == DIRECTION_AVOID])} to avoid.")
    reasoning_summary = " ".join(reasoning_parts)

    return {
        "strategy_id": strategy_id,
        "analyzed_research_context": analyzed,
        "recommended_research_directions": recommended_directions,
        "risk_notes": risk_notes[:15],
        "reasoning_summary": reasoning_summary,
        "timestamp": _ts(),
    }


def get_strategy_for_comparison(
    comparison_output: Dict[str, Any],
    *,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Convenience: get research strategy using a recent comparison output as context."""
    return get_research_strategy(
        workspace_id=workspace_id,
        comparison_output=comparison_output,
    )
