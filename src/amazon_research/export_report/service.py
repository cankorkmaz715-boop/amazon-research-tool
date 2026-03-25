"""
Step 228: Export/report service – workspace-scoped export payloads using existing APIs.
No heavy recomputation; no cross-workspace data. Safe failure behavior.
"""
from typing import Any, Dict, List, Optional, Tuple

from amazon_research.export_report.formatters import rows_to_csv


def get_export_dashboard(workspace_id: Optional[int], fmt: str = "json") -> Tuple[Optional[Dict], Optional[str], str]:
    """
    Return (payload_dict, csv_string, content_type).
    Dashboard export: JSON only (nested structure). CSV not applied.
    """
    if workspace_id is None:
        return None, None, "application/json"
    try:
        from amazon_research.api import get_workspace_dashboard_response
        body = get_workspace_dashboard_response(workspace_id=workspace_id)
        if body.get("error"):
            return None, None, "application/json"
        return body, None, "application/json"
    except Exception:
        return None, None, "application/json"


def get_export_opportunities(workspace_id: Optional[int], fmt: str = "json") -> Tuple[Optional[Dict], Optional[str], str]:
    """
    Return (payload_dict, csv_string, content_type).
    Opportunities from dashboard top_items.top_opportunities. Supports JSON and CSV.
    """
    if workspace_id is None:
        return {"data": [], "meta": {"workspace_id": None}}, None, "application/json"
    try:
        from amazon_research.api import get_workspace_dashboard_response
        body = get_workspace_dashboard_response(workspace_id=workspace_id)
        if body.get("error"):
            return None, None, "application/json"
        top = (body.get("top_items") or {}).get("top_opportunities") or []
        rows: List[Dict[str, Any]] = []
        for o in top:
            if isinstance(o, dict):
                rows.append({
                    "opportunity_id": o.get("opportunity_id"),
                    "strategy_status": o.get("strategy_status"),
                    "priority_level": o.get("priority_level"),
                    "opportunity_score": o.get("opportunity_score"),
                    "rationale": (o.get("rationale") or "")[:500],
                    "recommended_action": o.get("recommended_action"),
                })
        payload = {"data": rows, "meta": {"workspace_id": workspace_id, "count": len(rows)}}
        if fmt == "csv":
            cols = ["opportunity_id", "strategy_status", "priority_level", "opportunity_score", "rationale", "recommended_action"]
            csv_str = rows_to_csv(rows, cols)
            return payload, csv_str, "text/csv"
        return payload, None, "application/json"
    except Exception:
        return None, None, "application/json"


def get_export_portfolio(workspace_id: Optional[int], fmt: str = "json") -> Tuple[Optional[Dict], Optional[str], str]:
    """
    Return (payload_dict, csv_string, content_type).
    Portfolio list from existing API. Supports JSON and CSV.
    """
    if workspace_id is None:
        return {"data": [], "meta": {"workspace_id": None}}, None, "application/json"
    try:
        from amazon_research.api import get_workspace_portfolio_response
        body = get_workspace_portfolio_response(workspace_id=workspace_id, limit=1000)
        if body.get("error"):
            return None, None, "application/json"
        rows = body.get("data") or []
        payload = body
        if fmt == "csv":
            cols = ["id", "workspace_id", "item_type", "item_key", "item_label", "source_type", "status", "created_at", "updated_at"]
            csv_str = rows_to_csv(rows, cols)
            return payload, csv_str, "text/csv"
        return payload, None, "application/json"
    except Exception:
        return None, None, "application/json"


def get_export_alerts(workspace_id: Optional[int], fmt: str = "json") -> Tuple[Optional[Dict], Optional[str], str]:
    """
    Return (payload_dict, csv_string, content_type).
    Alerts from existing API. Supports JSON and CSV.
    """
    if workspace_id is None:
        return {"data": [], "meta": {"workspace_id": None}}, None, "application/json"
    try:
        from amazon_research.api import get_workspace_alerts_response
        body = get_workspace_alerts_response(workspace_id=workspace_id, limit=500)
        if body.get("error"):
            return None, None, "application/json"
        rows = body.get("data") or []
        payload = body
        if fmt == "csv":
            cols = ["id", "alert_type", "severity", "title", "description", "recorded_at", "read_at"]
            csv_str = rows_to_csv(rows, cols)
            return payload, csv_str, "text/csv"
        return payload, None, "application/json"
    except Exception:
        return None, None, "application/json"
