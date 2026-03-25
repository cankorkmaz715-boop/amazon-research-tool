"""
Step 221: Demo mode resolver. Decides when to use demo data for a workspace.
Demo activates when: (1) DEMO_MODE_ENABLED=true, OR (2) workspace has no opportunities,
no portfolio items, and no alerts. When real data exists, demo is not used.
"""
from typing import Any, Dict, Optional

from amazon_research.demo_data.config import is_demo_mode_enabled


def _has_any_opportunities(payload: Dict[str, Any]) -> bool:
    ov = payload.get("overview") or {}
    count = ov.get("total_opportunities")
    if count is not None and int(count) > 0:
        return True
    top = (payload.get("top_items") or {}).get("top_opportunities") or []
    return len(top) > 0


def _has_any_portfolio(payload: Dict[str, Any]) -> bool:
    ov = payload.get("overview") or {}
    count = ov.get("total_portfolio_items")
    if count is not None and int(count) > 0:
        return True
    ps = payload.get("portfolio_summary") or {}
    return int(ps.get("total") or 0) > 0


def _has_any_alerts(workspace_id: Optional[int]) -> bool:
    if workspace_id is None:
        return False
    try:
        from amazon_research.db import list_opportunity_alerts
        rows = list_opportunity_alerts(workspace_id=workspace_id, limit=1) or []
        return len(rows) > 0
    except Exception:
        return False


def should_use_demo_for_dashboard(workspace_id: Optional[int], real_payload: Dict[str, Any]) -> bool:
    """
    Return True if the dashboard should serve demo data instead of real_payload.
    - If DEMO_MODE_ENABLED is true, use demo when workspace would otherwise be empty.
    - If workspace has no opportunities, no portfolio items, and no alerts, use demo.
    - If real_payload already has is_demo=True, do not double-substitute.
    """
    if workspace_id is None:
        return False
    if real_payload.get("is_demo") is True:
        return False
    if is_demo_mode_enabled():
        if not _has_any_opportunities(real_payload) and not _has_any_portfolio(real_payload) and not _has_any_alerts(workspace_id):
            return True
        return False
    if not _has_any_opportunities(real_payload) and not _has_any_portfolio(real_payload) and not _has_any_alerts(workspace_id):
        return True
    return False


def should_use_demo_for_alerts(workspace_id: Optional[int]) -> bool:
    """Return True if alerts list should return demo alerts when workspace has no alerts."""
    if workspace_id is None:
        return False
    if _has_any_alerts(workspace_id):
        return False
    return True


def should_use_demo_for_portfolio(workspace_id: Optional[int], real_count: int) -> bool:
    """Return True if portfolio list should return demo items when workspace has no items."""
    if workspace_id is None:
        return False
    if real_count > 0:
        return False
    return True
