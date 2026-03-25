"""
Notification rules – workspace-scoped conditions for watchlists and research results. Step 44.
Lightweight evaluation only; no outbound delivery in this step.
Rule types: score_threshold, new_candidate, tracked_updated.
"""
import json
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

from .connection import get_connection

logger = get_logger("db.notification_rules")


def create_notification_rule(
    workspace_id: int,
    name: str,
    rule_type: str,
    params: Optional[Dict[str, Any]] = None,
    enabled: bool = True,
) -> int:
    """Create a notification rule. rule_type: score_threshold | new_candidate | tracked_updated. Returns id."""
    conn = get_connection()
    cur = conn.cursor()
    name_val = (name or "Rule").strip()
    type_val = (rule_type or "score_threshold").strip()
    params_val = json.dumps(params if isinstance(params, dict) else {})
    cur.execute(
        """
        INSERT INTO notification_rules (workspace_id, name, rule_type, params, enabled)
        VALUES (%s, %s, %s, %s::jsonb, %s)
        RETURNING id
        """,
        (workspace_id, name_val, type_val, params_val, enabled),
    )
    row = cur.fetchone()
    cur.close()
    conn.commit()
    return row[0]


def get_notification_rule(rule_id: int, workspace_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Load a rule by id. If workspace_id provided, returns None when rule is not in that workspace (Step 52)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, workspace_id, name, rule_type, params, enabled, created_at, updated_at FROM notification_rules WHERE id = %s",
        (rule_id,),
    )
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    if workspace_id is not None and row[1] != workspace_id:
        return None
    params = row[4]
    if hasattr(params, "copy"):
        params = dict(params)
    elif isinstance(params, str):
        try:
            params = json.loads(params)
        except Exception:
            params = {}
    return {
        "id": row[0],
        "workspace_id": row[1],
        "name": row[2],
        "rule_type": row[3],
        "params": params or {},
        "enabled": row[5],
        "created_at": row[6],
        "updated_at": row[7],
    }


def list_notification_rules(workspace_id: int, enabled_only: bool = False) -> List[Dict[str, Any]]:
    """List rules for the workspace. Optionally filter by enabled=True."""
    conn = get_connection()
    cur = conn.cursor()
    if enabled_only:
        cur.execute(
            """
            SELECT id, workspace_id, name, rule_type, params, enabled, created_at, updated_at
            FROM notification_rules WHERE workspace_id = %s AND enabled = true ORDER BY id
            """,
            (workspace_id,),
        )
    else:
        cur.execute(
            """
            SELECT id, workspace_id, name, rule_type, params, enabled, created_at, updated_at
            FROM notification_rules WHERE workspace_id = %s ORDER BY id
            """,
            (workspace_id,),
        )
    rows = cur.fetchall()
    cur.close()
    out = []
    for row in rows:
        params = row[4]
        if hasattr(params, "copy"):
            params = dict(params)
        elif isinstance(params, str):
            try:
                params = json.loads(params)
            except Exception:
                params = {}
        out.append({
            "id": row[0],
            "workspace_id": row[1],
            "name": row[2],
            "rule_type": row[3],
            "params": params or {},
            "enabled": row[5],
            "created_at": row[6],
            "updated_at": row[7],
        })
    return out


def evaluate_rule(rule_id: int, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate a rule against context. No delivery; returns whether the rule matches.
    context examples:
      score_threshold: {"event": "score_threshold", "score_field": "opportunity_score", "value": 75}
      new_candidate: {"event": "new_candidate", "asin_id": 1}
      tracked_updated: {"event": "tracked_updated", "watchlist_id": 1, "asin_id": 1}
    Returns: {"matches": bool, "reason": str or None}
    """
    rule = get_notification_rule(rule_id)
    if not rule:
        return {"matches": False, "reason": "rule not found"}
    if not rule.get("enabled", True):
        return {"matches": False, "reason": "rule disabled"}
    return _evaluate_condition(rule["rule_type"], rule.get("params") or {}, context)


def _evaluate_condition(rule_type: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Internal: evaluate one rule type against context."""
    event = (context.get("event") or "").strip()
    if rule_type == "score_threshold":
        score_field = (params.get("score_field") or "opportunity_score").strip()
        op = (params.get("operator") or ">=").strip()
        threshold = params.get("value")
        if threshold is None:
            return {"matches": False, "reason": "missing threshold value"}
        try:
            threshold = float(threshold)
        except (TypeError, ValueError):
            return {"matches": False, "reason": "invalid threshold"}
        ctx_value = context.get("value") if "value" in context else context.get(score_field)
        if ctx_value is None:
            return {"matches": False, "reason": "no value in context"}
        try:
            ctx_value = float(ctx_value)
        except (TypeError, ValueError):
            return {"matches": False, "reason": "invalid context value"}
        if op == ">=" and ctx_value >= threshold:
            return {"matches": True, "reason": f"{score_field} {ctx_value} >= {threshold}"}
        if op == ">" and ctx_value > threshold:
            return {"matches": True, "reason": f"{score_field} {ctx_value} > {threshold}"}
        if op == "<=" and ctx_value <= threshold:
            return {"matches": True, "reason": f"{score_field} {ctx_value} <= {threshold}"}
        if op == "<" and ctx_value < threshold:
            return {"matches": True, "reason": f"{score_field} {ctx_value} < {threshold}"}
        return {"matches": False, "reason": f"threshold not met ({ctx_value} {op} {threshold})"}

    if rule_type == "new_candidate":
        if event == "new_candidate":
            return {"matches": True, "reason": "new candidate"}
        return {"matches": False, "reason": "not a new_candidate event"}

    if rule_type == "tracked_updated":
        if event != "tracked_updated":
            return {"matches": False, "reason": "not a tracked_updated event"}
        watchlist_id = params.get("watchlist_id")
        if watchlist_id is not None and context.get("watchlist_id") != watchlist_id:
            return {"matches": False, "reason": "watchlist_id mismatch"}
        return {"matches": True, "reason": "tracked item updated"}

    return {"matches": False, "reason": f"unknown rule_type: {rule_type}"}
