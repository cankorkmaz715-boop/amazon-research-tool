"""
Step 189: Opportunity alert engine – generate alerts for high-potential opportunities from the ranking engine.
Identifies opportunities exceeding alert thresholds; produces alert records (opportunity id, market, score, reason, timestamp).
Stores in opportunity_alerts. Compatible with ranking engine, scheduler loop, workspace feed, research copilot.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_alert_engine")

# Default score threshold above which we generate an alert
DEFAULT_SCORE_THRESHOLD = 70.0
# Alert type for threshold-based alerts
ALERT_TYPE_HIGH_POTENTIAL = "high_potential"
ALERT_TYPE_SCORE_THRESHOLD = "score_threshold"
TARGET_TYPE_OPPORTUNITY = "opportunity"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_market_from_ref(opportunity_ref: str) -> str:
    """Extract market from opportunity_ref e.g. DE:B08 -> DE."""
    ref = (opportunity_ref or "").strip()
    if ":" in ref:
        return ref.split(":", 1)[0].strip().upper() or "DE"
    return "DE"


def build_alert_record(
    opportunity_id: str,
    score: float,
    reason: str,
    market: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Build one alert record for persistence. Includes opportunity id, market, score, reason, timestamp.
    Shape compatible with save_opportunity_alert (target_entity, alert_type, triggering_signals).
    """
    ts = timestamp or _now_utc()
    m = (market or _parse_market_from_ref(opportunity_id)).strip().upper()
    return {
        "target_type": TARGET_TYPE_OPPORTUNITY,
        "target_entity": (opportunity_id or "").strip(),
        "alert_type": ALERT_TYPE_HIGH_POTENTIAL,
        "triggering_signals": {
            "market": m,
            "score": round(float(score), 2),
            "reason": (reason or "score above threshold").strip(),
            "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
        },
        "recorded_at": ts,
    }


def identify_alerts_from_rankings(
    rankings: List[Dict[str, Any]],
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> List[Dict[str, Any]]:
    """
    From ranking engine output, identify opportunities exceeding score_threshold.
    Returns list of alert records (opportunity id, market, score, reason, timestamp).
    """
    alerts: List[Dict[str, Any]] = []
    for r in rankings or []:
        ref = (r.get("opportunity_ref") or "").strip()
        score = r.get("opportunity_score")
        if not ref:
            continue
        try:
            score_f = float(score) if score is not None else 0.0
        except (TypeError, ValueError):
            score_f = 0.0
        if score_f < score_threshold:
            continue
        market = _parse_market_from_ref(ref)
        reason = f"opportunity_score {score_f:.0f} above threshold {score_threshold:.0f}"
        alerts.append(build_alert_record(ref, score_f, reason, market=market))
    return alerts


def run_alert_detection(
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    limit_rankings: int = 50,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load latest rankings from ranking engine, identify those above threshold, return alert records.
    Does not persist; use persist_alerts to save.
    Step 198: When workspace_id is set, consults workspace alert preferences for threshold and gating.
    """
    effective_threshold = score_threshold
    if workspace_id is not None:
        try:
            from amazon_research.workspace_alert_preferences import get_effective_alert_settings, should_produce_opportunity_alerts
            if not should_produce_opportunity_alerts(workspace_id):
                return []
            prefs = get_effective_alert_settings(workspace_id)
            effective_threshold = float(prefs.get("score_threshold", score_threshold))
        except Exception as e:
            logger.debug("run_alert_detection alert preferences: %s", e)
    try:
        from amazon_research.db.opportunity_rankings import get_latest_rankings
        rankings = get_latest_rankings(limit=limit_rankings)
    except Exception as e:
        logger.debug("run_alert_detection get_latest_rankings: %s", e)
        rankings = []
    return identify_alerts_from_rankings(rankings, score_threshold=effective_threshold)


def persist_alerts(
    alerts: List[Dict[str, Any]],
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Persist alert records to opportunity_alerts. Returns saved_count and ids."""
    ids: List[int] = []
    try:
        from amazon_research.db import save_opportunity_alert
        for a in alerts or []:
            rid = save_opportunity_alert(a, workspace_id=workspace_id)
            if rid is not None:
                ids.append(rid)
    except Exception as e:
        logger.debug("persist_alerts: %s", e)
    return {"saved_count": len(ids), "ids": ids}


def run_and_persist_alerts(
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
    limit_rankings: int = 50,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Run alert detection from rankings and persist to opportunity_alerts.
    Compatible with scheduler loop: call after ranking engine run.
    Step 198: When workspace_id is set, run_alert_detection uses workspace alert preferences (threshold + gating).
    """
    alerts = run_alert_detection(score_threshold=score_threshold, limit_rankings=limit_rankings, workspace_id=workspace_id)
    result = persist_alerts(alerts, workspace_id=workspace_id)
    result["alerts"] = alerts
    result["alert_count"] = len(alerts)
    return result


def get_alerts_for_workspace_feed(
    workspace_id: Optional[int] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    List recent opportunity alerts for workspace feed / copilot. Returns list of alert dicts
    with opportunity id (target_entity), market, score, reason from triggering_signals, timestamp (recorded_at).
    """
    try:
        from amazon_research.db import list_opportunity_alerts
        rows = list_opportunity_alerts(limit=limit, workspace_id=workspace_id)
    except Exception as e:
        logger.debug("get_alerts_for_workspace_feed: %s", e)
        return []
    out = []
    for r in rows:
        sig = r.get("triggering_signals") or {}
        out.append({
            "opportunity_id": r.get("target_entity"),
            "market": sig.get("market"),
            "score": sig.get("score"),
            "reason": sig.get("reason"),
            "timestamp": r.get("recorded_at"),
            "alert_type": r.get("alert_type"),
            "id": r.get("id"),
        })
    return out
