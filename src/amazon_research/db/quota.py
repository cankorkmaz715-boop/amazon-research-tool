"""
Workspace quota model v1. Step 54 – limits per category; integrates with usage tracking.
Step 55: check_quota_and_raise for enforcement; QuotaExceededError for clear failure.
"""
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection
from .usage import get_usage_summary_for_workspace

logger = get_logger("db.quota")


def _get_effective_quota_limit(workspace_id: int, quota_type: str) -> tuple[Optional[int], int]:
    """
    Step 60: Return (limit, period_days) from workspace_quotas row, or from workspace's plan.quota_profile, or (None, 30).
    """
    quota = get_workspace_quota(workspace_id, quota_type)
    if quota:
        return quota["limit_value"], quota["period_days"]
    try:
        from .plans import get_workspace_plan
        plan = get_workspace_plan(workspace_id)
        if plan and plan.get("active") and plan.get("quota_profile") and isinstance(plan["quota_profile"], dict):
            limit = plan["quota_profile"].get(quota_type)
            if limit is not None and isinstance(limit, (int, float)):
                return int(limit), 30
    except Exception:
        pass
    return None, 30


class QuotaExceededError(Exception):
    """Raised when workspace quota is exceeded. Step 55 enforcement."""
    def __init__(self, quota_type: str, limit: int, used: int, remaining: int, message: Optional[str] = None):
        self.quota_type = quota_type
        self.limit = limit
        self.used = used
        self.remaining = remaining
        super().__init__(message or f"quota exceeded: {quota_type} (limit={limit}, used={used})")


def set_workspace_quota(
    workspace_id: int,
    quota_type: str,
    limit_value: int,
    period_days: int = 30,
) -> None:
    """
    Set or update a quota for the workspace. Upserts by (workspace_id, quota_type).
    limit_value: max count in the period. period_days: rolling window (e.g. 30 = per 30 days).
    """
    if limit_value < 0:
        raise ValueError("limit_value must be non-negative")
    if period_days < 1:
        raise ValueError("period_days must be positive")
    conn = get_connection()
    cur = conn.cursor()
    qtype = (quota_type or "").strip()
    cur.execute(
        """
        INSERT INTO workspace_quotas (workspace_id, quota_type, limit_value, period_days, updated_at)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (workspace_id, quota_type)
        DO UPDATE SET limit_value = EXCLUDED.limit_value, period_days = EXCLUDED.period_days, updated_at = NOW()
        """,
        (workspace_id, qtype, limit_value, period_days),
    )
    cur.close()
    conn.commit()


def get_workspace_quota(workspace_id: int, quota_type: str) -> Optional[Dict[str, Any]]:
    """Return quota row as dict (id, workspace_id, quota_type, limit_value, period_days, created_at, updated_at) or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, workspace_id, quota_type, limit_value, period_days, created_at, updated_at
        FROM workspace_quotas
        WHERE workspace_id = %s AND quota_type = %s
        """,
        (workspace_id, (quota_type or "").strip()),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "id": row[0],
        "workspace_id": row[1],
        "quota_type": row[2],
        "limit_value": row[3],
        "period_days": row[4],
        "created_at": row[5],
        "updated_at": row[6],
    }


def list_workspace_quotas(workspace_id: int) -> List[Dict[str, Any]]:
    """Return all quotas for the workspace."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, workspace_id, quota_type, limit_value, period_days, created_at, updated_at
        FROM workspace_quotas
        WHERE workspace_id = %s
        ORDER BY quota_type
        """,
        (workspace_id,),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        {
            "id": r[0],
            "workspace_id": r[1],
            "quota_type": r[2],
            "limit_value": r[3],
            "period_days": r[4],
            "created_at": r[5],
            "updated_at": r[6],
        }
        for r in rows
    ]


def check_quota(
    workspace_id: int,
    quota_type: str,
    since_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Lightweight evaluation helper: compare usage to quota for the workspace.
    Step 60: limit may come from workspace_quotas or from workspace's plan.quota_profile.
    Returns dict: allowed (bool), limit (int or None), used (int), remaining (int or None).
    """
    limit, default_period = _get_effective_quota_limit(workspace_id, quota_type)
    period = since_days if since_days is not None else default_period
    usage = get_usage_summary_for_workspace(workspace_id, since_days=period)
    used = usage.get(quota_type, 0)

    if limit is None:
        return {
            "allowed": True,
            "limit": None,
            "used": used,
            "remaining": None,
        }

    remaining = max(0, limit - used)
    return {
        "allowed": used < limit,
        "limit": limit,
        "used": used,
        "remaining": remaining,
    }


def check_quota_and_raise(workspace_id: int, quota_type: str, since_days: Optional[int] = None) -> None:
    """
    If quota is set and exceeded, audit log and raise QuotaExceededError. Otherwise no-op. Step 55/56.
    """
    result = check_quota(workspace_id, quota_type, since_days=since_days)
    if not result["allowed"] and result["limit"] is not None:
        try:
            from .audit import record_audit
            record_audit(workspace_id, "quota_exceeded", {"quota_type": quota_type, "limit": result["limit"], "used": result["used"]})
        except Exception:
            pass
        try:
            from .billing import record_billable_event
            record_billable_event(workspace_id, "quota_overage", {"quota_type": quota_type, "limit": result["limit"], "used": result["used"]})
        except Exception:
            pass
        raise QuotaExceededError(
            quota_type=quota_type,
            limit=result["limit"],
            used=result["used"],
            remaining=result["remaining"],
        )
