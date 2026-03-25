"""
Step 177: Workspace risk/reward map – map opportunities into risk/reward quadrants.
Risk: competition, signal volatility, lifecycle instability, anomaly alerts, trend instability.
Reward: demand, trend strength, opportunity score, niche growth. Quadrants: low_risk_low_reward, etc.
Integrates with lifecycle engine, predictive watch, portfolio tracker, portfolio strategy insights, dashboards.
Rule-based, deterministic. Does not modify crawler, worker, auth, billing, UI.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.risk_reward_map")

# Quadrant classifications
QUADRANT_LOW_RISK_LOW_REWARD = "low_risk_low_reward"
QUADRANT_LOW_RISK_HIGH_REWARD = "low_risk_high_reward"
QUADRANT_HIGH_RISK_HIGH_REWARD = "high_risk_high_reward"
QUADRANT_HIGH_RISK_LOW_REWARD = "high_risk_low_reward"

QUADRANTS = [
    QUADRANT_LOW_RISK_LOW_REWARD,
    QUADRANT_LOW_RISK_HIGH_REWARD,
    QUADRANT_HIGH_RISK_HIGH_REWARD,
    QUADRANT_HIGH_RISK_LOW_REWARD,
]

RISK_REWARD_THRESHOLD = 50  # >= 50 = high


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp_score(v: float) -> float:
    return round(max(0.0, min(100.0, float(v))), 1)


def get_risk_reward_for_opportunity(
    opportunity_ref: str,
    *,
    memory_record: Optional[Dict[str, Any]] = None,
    lifecycle_output: Optional[Dict[str, Any]] = None,
    anomaly_alert_count: int = 0,
    drift_reports: Optional[Sequence[Dict[str, Any]]] = None,
    competition_score: Optional[float] = None,
    demand_score: Optional[float] = None,
    opportunity_score: Optional[float] = None,
    trend_score: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compute risk score, reward score, and quadrant for one opportunity. Returns:
    opportunity_id, risk_score, reward_score, quadrant_classification, signal_summary, timestamp.
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "opportunity_id": ref,
        "risk_score": 50.0,
        "reward_score": 50.0,
        "quadrant_classification": QUADRANT_LOW_RISK_LOW_REWARD,
        "signal_summary": {},
        "timestamp": _now_iso(),
    }
    if not ref:
        out["signal_summary"] = {"error": "missing ref"}
        return out

    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_risk_reward_for_opportunity get_opportunity_memory: %s", e)

    life = lifecycle_output
    if life is None and mem:
        try:
            from amazon_research.discovery.opportunity_lifecycle_engine import get_lifecycle_state
            life = get_lifecycle_state(ref, memory_record=mem)
        except Exception as e:
            logger.debug("get_risk_reward_for_opportunity get_lifecycle_state: %s", e)

    # Resolve scores from memory or kwargs
    ctx = (mem or {}).get("context") or mem or {}
    comp = competition_score if competition_score is not None else _float(ctx, "competition_score", "competition")
    demand = demand_score if demand_score is not None else _float(ctx, "demand_score", "demand")
    opp_score = opportunity_score if opportunity_score is not None else _float(ctx, "latest_opportunity_score", "opportunity_score") or _float(ctx, "opportunity_score")
    trend = trend_score if trend_score is not None else _float(ctx, "trend_score", "trend")
    if opp_score is None and mem:
        opp_score = mem.get("latest_opportunity_score")

    lifecycle_state = (life or {}).get("lifecycle_state") or ""
    lifecycle_score = (life or {}).get("lifecycle_score") or 50
    supporting = (life or {}).get("supporting_signal_summary") or {}
    score_trend = (supporting.get("score_trend") or "flat").strip().lower()
    drift_list = list(drift_reports or [])
    drift_collapse = sum(1 for d in drift_list if (d.get("drift_type") or "").lower() == "collapse")
    drift_spike = sum(1 for d in drift_list if (d.get("drift_type") or "").lower() == "spike")
    drift_count = len(drift_list)

    # --- Risk components (0-100, higher = riskier) ---
    risk_comp = 0.0
    risk_n = 0
    if comp is not None:
        risk_comp += min(100, comp * 1.2)
        risk_n += 1
    else:
        risk_comp += 50
        risk_n += 1
    if lifecycle_state in ("weakening", "fading"):
        risk_comp += 70
        risk_n += 1
    elif lifecycle_state in ("emerging", "rising", "accelerating"):
        risk_comp += 25
        risk_n += 1
    else:
        risk_comp += 40
        risk_n += 1
    if anomaly_alert_count > 0:
        risk_comp += min(80, 30 + anomaly_alert_count * 15)
        risk_n += 1
    if drift_collapse > 0:
        risk_comp += 60
        risk_n += 1
    if drift_count >= 3:
        risk_comp += 40
        risk_n += 1
    if score_trend == "down":
        risk_comp += 50
        risk_n += 1
    risk_score = _clamp_score(risk_comp / max(1, risk_n))

    # --- Reward components (0-100, higher = better) ---
    reward_comp = 0.0
    reward_n = 0
    if demand is not None:
        reward_comp += min(100, demand)
        reward_n += 1
    else:
        reward_comp += 50
        reward_n += 1
    if opp_score is not None:
        reward_comp += min(100, float(opp_score))
        reward_n += 1
    else:
        reward_comp += lifecycle_score or 50
        reward_n += 1
    if lifecycle_state in ("rising", "accelerating"):
        reward_comp += 75
        reward_n += 1
    elif lifecycle_state in ("emerging", "maturing"):
        reward_comp += 55
        reward_n += 1
    else:
        reward_comp += 30
        reward_n += 1
    if score_trend == "up":
        reward_comp += 65
        reward_n += 1
    elif score_trend == "flat":
        reward_comp += 45
        reward_n += 1
    if trend is not None and float(trend) > 0:
        reward_comp += min(80, 40 + float(trend))
        reward_n += 1
    reward_score = _clamp_score(reward_comp / max(1, reward_n))

    # --- Quadrant ---
    high_risk = risk_score >= RISK_REWARD_THRESHOLD
    high_reward = reward_score >= RISK_REWARD_THRESHOLD
    if high_risk and high_reward:
        quadrant = QUADRANT_HIGH_RISK_HIGH_REWARD
    elif high_risk and not high_reward:
        quadrant = QUADRANT_HIGH_RISK_LOW_REWARD
    elif not high_risk and high_reward:
        quadrant = QUADRANT_LOW_RISK_HIGH_REWARD
    else:
        quadrant = QUADRANT_LOW_RISK_LOW_REWARD

    out["risk_score"] = risk_score
    out["reward_score"] = reward_score
    out["quadrant_classification"] = quadrant
    out["signal_summary"] = {
        "competition_score": comp,
        "demand_score": demand,
        "opportunity_score": opp_score,
        "trend_score": trend,
        "lifecycle_state": lifecycle_state,
        "lifecycle_score": lifecycle_score,
        "score_trend": score_trend,
        "anomaly_alert_count": anomaly_alert_count,
        "drift_count": drift_count,
        "drift_collapse": drift_collapse,
        "drift_spike": drift_spike,
    }
    return out


def _float(ctx: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = ctx.get(k)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    return None


def get_workspace_risk_reward_map(
    workspace_id: int,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Build risk/reward map for all opportunities in the workspace portfolio (or opportunity memory).
    Returns list of risk/reward outputs for dashboard and portfolio compatibility.
    """
    try:
        from amazon_research.discovery.opportunity_portfolio_tracker import get_workspace_portfolio
        portfolio = get_workspace_portfolio(workspace_id, limit=limit)
        refs = set()
        for it in portfolio:
            ent = it.get("target_entity") or {}
            r = ent.get("ref") or it.get("opportunity_ref")
            if r:
                refs.add(r)
        if not refs:
            from amazon_research.db import list_opportunity_memory
            rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
            refs = {r.get("opportunity_ref") for r in rows if r.get("opportunity_ref")}
        results: List[Dict[str, Any]] = []
        for ref in list(refs)[:limit]:
            results.append(get_risk_reward_for_opportunity(ref, memory_record=None))
        return results
    except Exception as e:
        logger.debug("get_workspace_risk_reward_map: %s", e)
        return []


def get_risk_reward_for_portfolio_item(
    portfolio_item: Dict[str, Any],
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute risk/reward for a single portfolio tracker item. Uses target_entity.ref as opportunity_id.
    """
    ent = portfolio_item.get("target_entity") or {}
    ref = ent.get("ref") or portfolio_item.get("opportunity_ref") or ""
    return get_risk_reward_for_opportunity(ref, memory_record=None)
