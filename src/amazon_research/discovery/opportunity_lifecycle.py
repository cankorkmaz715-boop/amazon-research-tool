"""
Step 125: Opportunity lifecycle tracker – classify opportunities into lifecycle states.
Uses opportunity memory (first_seen_at, last_seen_at, score evolution, status). Rule-based, explainable.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("discovery.opportunity_lifecycle")

LIFECYCLE_NEW = "new"
LIFECYCLE_RISING = "rising"
LIFECYCLE_STABLE = "stable"
LIFECYCLE_WEAKENING = "weakening"
LIFECYCLE_FADING = "fading"

DAYS_FADING = 30
DAYS_NEW = 7


def _parse_dt(v: Any) -> Optional[datetime]:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _days_ago(dt: Optional[datetime]) -> Optional[float]:
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    return delta.total_seconds() / (24 * 3600)


def _score_trend(score_history: List[Dict[str, Any]], last_n: int = 5) -> Optional[str]:
    """Return 'up', 'down', or 'flat' from recent score history."""
    if not score_history or not isinstance(score_history, list):
        return None
    points = [p.get("score") for p in score_history if isinstance(p, dict) and p.get("score") is not None]
    points = points[-last_n:] if len(points) > last_n else points
    if len(points) < 2:
        return None
    first = points[0]
    last = points[-1]
    if last > first:
        return "up"
    if last < first:
        return "down"
    return "flat"


def get_opportunity_lifecycle(
    opportunity_ref: str,
    *,
    memory_record: Optional[Dict[str, Any]] = None,
    fading_days: float = DAYS_FADING,
    new_days: float = DAYS_NEW,
) -> Dict[str, Any]:
    """
    Classify opportunity into lifecycle state from memory. Returns:
    opportunity_id, lifecycle_state, rationale, confidence, supporting_signals.
    """
    ref = (opportunity_ref or "").strip()
    out: Dict[str, Any] = {
        "opportunity_id": ref,
        "lifecycle_state": LIFECYCLE_STABLE,
        "rationale": "",
        "confidence": "medium",
        "supporting_signals": {},
    }
    if not ref:
        out["rationale"] = "missing opportunity_ref"
        return out

    mem = memory_record
    if mem is None:
        try:
            from amazon_research.db import get_opportunity_memory
            mem = get_opportunity_memory(ref)
        except Exception as e:
            logger.debug("get_opportunity_lifecycle get_opportunity_memory failed: %s", e)
    if not mem:
        out["rationale"] = "no memory record"
        out["supporting_signals"] = {"memory": "absent"}
        return out

    first_seen = _parse_dt(mem.get("first_seen_at"))
    last_seen = _parse_dt(mem.get("last_seen_at"))
    status = (mem.get("status") or "").strip()
    score_history = mem.get("score_history") or []
    latest_score = mem.get("latest_opportunity_score")

    last_seen_days = _days_ago(last_seen)
    first_seen_days = _days_ago(first_seen)
    out["supporting_signals"] = {
        "memory_status": status,
        "last_seen_days_ago": round(last_seen_days, 1) if last_seen_days is not None else None,
        "first_seen_days_ago": round(first_seen_days, 1) if first_seen_days is not None else None,
        "score_history_length": len(score_history) if isinstance(score_history, list) else 0,
        "latest_score": latest_score,
        "score_trend": _score_trend(score_history),
    }

    # Rule order: fading first, then rising/weakening from status/trend, then new, else stable
    if last_seen_days is not None and last_seen_days >= fading_days:
        out["lifecycle_state"] = LIFECYCLE_FADING
        out["rationale"] = f"last_seen {last_seen_days:.0f} days ago (>= {fading_days})"
        out["confidence"] = "high"
        return out

    if status == "strengthening" or out["supporting_signals"].get("score_trend") == "up":
        out["lifecycle_state"] = LIFECYCLE_RISING
        out["rationale"] = "score strengthening or upward trend"
        out["confidence"] = "high" if status == "strengthening" else "medium"
        return out

    if status == "weakening" or out["supporting_signals"].get("score_trend") == "down":
        out["lifecycle_state"] = LIFECYCLE_WEAKENING
        out["rationale"] = "score weakening or downward trend"
        out["confidence"] = "high" if status == "weakening" else "medium"
        return out

    if status == "newly_discovered" and (first_seen_days is not None and first_seen_days <= new_days or len(score_history) <= 1):
        out["lifecycle_state"] = LIFECYCLE_NEW
        out["rationale"] = "newly discovered, recent first_seen or single observation"
        out["confidence"] = "high"
        return out

    out["lifecycle_state"] = LIFECYCLE_STABLE
    out["rationale"] = "recurring with stable or flat trend"
    out["confidence"] = "medium"
    return out


def list_opportunities_with_lifecycle(
    limit: int = 50,
    lifecycle_state: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List opportunity memory rows with lifecycle classification. Optional filter by lifecycle_state."""
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=limit, workspace_id=workspace_id)
        out = []
        for mem in rows:
            ref = mem.get("opportunity_ref")
            if not ref:
                continue
            life = get_opportunity_lifecycle(ref, memory_record=mem)
            if lifecycle_state is not None and life.get("lifecycle_state") != lifecycle_state:
                continue
            out.append({**mem, "lifecycle": life})
        return out
    except Exception as e:
        logger.debug("list_opportunities_with_lifecycle failed: %s", e)
        return []
