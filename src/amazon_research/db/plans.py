"""
Plan model v1. Step 59 – subscription/plan for workspaces; quota profile and billing metadata.
Lightweight, DB-friendly. No payment provider logic.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.plans")


def create_plan(
    name: str,
    active: bool = True,
    quota_profile: Optional[Dict[str, Any]] = None,
    billing_metadata: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Create a plan. quota_profile: e.g. {"discovery_run": 10, "export_csv": 5, "api_request": 100}.
    billing_metadata: optional e.g. {"stripe_price_id": null} for future use.
    Returns plans.id.
    """
    conn = get_connection()
    cur = conn.cursor()
    name_val = (name or "Plan").strip()
    quota_json = json.dumps(quota_profile) if isinstance(quota_profile, dict) else None
    billing_json = json.dumps(billing_metadata) if isinstance(billing_metadata, dict) else None
    cur.execute(
        """
        INSERT INTO plans (name, active, quota_profile, billing_metadata)
        VALUES (%s, %s, %s::jsonb, %s::jsonb)
        RETURNING id
        """,
        (name_val, bool(active), quota_json, billing_json),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def get_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    """Return plan dict (id, name, active, quota_profile, billing_metadata, created_at, updated_at) or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, active, quota_profile, billing_metadata, created_at, updated_at FROM plans WHERE id = %s",
        (plan_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "active": row[2],
        "quota_profile": row[3] if isinstance(row[3], dict) else (json.loads(row[3]) if row[3] else None),
        "billing_metadata": row[4] if isinstance(row[4], dict) else (json.loads(row[4]) if row[4] else None),
        "created_at": row[5],
        "updated_at": row[6],
    }


def list_plans(active_only: bool = False) -> List[Dict[str, Any]]:
    """Return all plans (or only active)."""
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        cur.execute(
            "SELECT id, name, active, quota_profile, billing_metadata, created_at, updated_at FROM plans WHERE active = true ORDER BY id"
        )
    else:
        cur.execute(
            "SELECT id, name, active, quota_profile, billing_metadata, created_at, updated_at FROM plans ORDER BY id"
        )
    rows = cur.fetchall()
    cur.close()
    out = []
    for r in rows:
        out.append({
            "id": r[0],
            "name": r[1],
            "active": r[2],
            "quota_profile": r[3] if isinstance(r[3], dict) else (json.loads(r[3]) if r[3] else None),
            "billing_metadata": r[4] if isinstance(r[4], dict) else (json.loads(r[4]) if r[4] else None),
            "created_at": r[5],
            "updated_at": r[6],
        })
    return out


def set_workspace_plan(workspace_id: int, plan_id: Optional[int]) -> None:
    """Set the plan for a workspace. plan_id None clears the link."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE workspaces SET plan_id = %s, updated_at = NOW() WHERE id = %s",
        (plan_id, workspace_id),
    )
    cur.close()
    conn.commit()


def get_workspace_plan(workspace_id: int) -> Optional[Dict[str, Any]]:
    """Return the plan linked to the workspace, or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT plan_id FROM workspaces WHERE id = %s", (workspace_id,))
    row = cur.fetchone()
    cur.close()
    if not row or row[0] is None:
        return None
    return get_plan(row[0])
