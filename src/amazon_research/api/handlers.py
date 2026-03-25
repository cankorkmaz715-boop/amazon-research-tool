"""
Read-only API handlers. Dashboard-ready: stable envelope { data, meta }, filtering and sorting. DB-only.
Step 28: response contracts for dashboard consumption; limit, offset, sort_by, order.
"""
from decimal import Decimal
from datetime import datetime
from typing import Any, Dict, List, Optional

from amazon_research.db import get_connection, get_watchlist, list_saved_views, list_watchlists, list_watchlist_items

_LIMIT = 500

# Step 52: workspace isolation – error envelope when scope is missing/invalid
def _scope_error(message: str, limit: int, offset: int) -> Dict[str, Any]:
    """Return error envelope for missing or invalid workspace scope."""
    return {
        "error": message,
        "data": [],
        "meta": {"count": 0, "limit": limit, "offset": offset},
    }
_DEFAULT_SORT = {"products": "created_at", "metrics": "updated_at", "scores": "scored_at"}

# Allowed sort columns per endpoint (safe for ORDER BY)
_PRODUCTS_SORT: Dict[str, str] = {"created_at": "created_at", "updated_at": "updated_at", "asin": "asin"}
_METRICS_SORT: Dict[str, str] = {"updated_at": "pm.updated_at", "price": "pm.price", "rating": "pm.rating", "review_count": "pm.review_count"}
_SCORES_SORT: Dict[str, str] = {"scored_at": "sr.scored_at", "opportunity_score": "sr.opportunity_score", "demand_score": "sr.demand_score"}


def _serialize(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _envelope(data: List[Dict[str, Any]], count: int, limit: int, offset: int) -> Dict[str, Any]:
    """Stable dashboard contract: { data, meta }."""
    return {
        "data": data,
        "meta": {"count": count, "limit": limit, "offset": offset},
    }


def get_products(
    limit: int = _LIMIT,
    offset: int = 0,
    sort_by: Optional[str] = None,
    order: str = "desc",
    category: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Discovered products. Returns { data, meta }. workspace_id required (Step 52 isolation)."""
    if workspace_id is None:
        return _scope_error("workspace_id required", limit, offset)
    conn = get_connection()
    cur = conn.cursor()
    sort_col = _PRODUCTS_SORT.get(sort_by or "created_at", "created_at")
    order_val = "DESC" if (order or "desc").lower() == "desc" else "ASC"
    conditions = []
    params: List[Any] = []
    if category:
        conditions.append("category = %s")
        params.append(category)
    if workspace_id is not None:
        conditions.append("workspace_id = %s")
        params.append(workspace_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    cur.execute(f"SELECT COUNT(*) FROM asins {where}", params)
    total = cur.fetchone()[0]
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT asin, title, brand, category, product_url, main_image_url, created_at, updated_at
        FROM asins {where}
        ORDER BY {sort_col} {order_val} NULLS LAST
        LIMIT %s OFFSET %s
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    keys = ["asin", "title", "brand", "category", "product_url", "main_image_url", "created_at", "updated_at"]
    data = [dict(zip(keys, [_serialize(v) for v in row])) for row in rows]
    return _envelope(data, total, limit, offset)


def get_metrics(
    limit: int = _LIMIT,
    offset: int = 0,
    sort_by: Optional[str] = None,
    order: str = "desc",
    asin: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Refreshed metrics. Returns { data, meta }. workspace_id required (Step 52 isolation)."""
    if workspace_id is None:
        return _scope_error("workspace_id required", limit, offset)
    conn = get_connection()
    cur = conn.cursor()
    sort_col = _METRICS_SORT.get(sort_by or "updated_at", "pm.updated_at")
    order_val = "DESC" if (order or "desc").lower() == "desc" else "ASC"
    conditions = []
    params: List[Any] = []
    if asin:
        conditions.append("a.asin = %s")
        params.append(asin)
    if workspace_id is not None:
        conditions.append("a.workspace_id = %s")
        params.append(workspace_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    cur.execute(
        f"SELECT COUNT(*) FROM product_metrics pm JOIN asins a ON a.id = pm.asin_id {where}",
        params,
    )
    total = cur.fetchone()[0]
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT a.asin, pm.price, pm.currency, pm.bsr, pm.rating, pm.review_count, pm.seller_count, pm.updated_at
        FROM product_metrics pm
        JOIN asins a ON a.id = pm.asin_id {where}
        ORDER BY {sort_col} {order_val} NULLS LAST
        LIMIT %s OFFSET %s
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    keys = ["asin", "price", "currency", "bsr", "rating", "review_count", "seller_count", "updated_at"]
    data = [dict(zip(keys, [_serialize(v) for v in row])) for row in rows]
    return _envelope(data, total, limit, offset)


def get_scores(
    limit: int = _LIMIT,
    offset: int = 0,
    sort_by: Optional[str] = None,
    order: str = "desc",
    asin: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Scoring results. Returns { data, meta }. workspace_id required (Step 52 isolation)."""
    if workspace_id is None:
        return _scope_error("workspace_id required", limit, offset)
    conn = get_connection()
    cur = conn.cursor()
    sort_col = _SCORES_SORT.get(sort_by or "scored_at", "sr.scored_at")
    order_val = "DESC" if (order or "desc").lower() == "desc" else "ASC"
    conditions = []
    params: List[Any] = []
    if asin:
        conditions.append("a.asin = %s")
        params.append(asin)
    if workspace_id is not None:
        conditions.append("a.workspace_id = %s")
        params.append(workspace_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    cur.execute(
        f"SELECT COUNT(*) FROM scoring_results sr JOIN asins a ON a.id = sr.asin_id {where}",
        params,
    )
    total = cur.fetchone()[0]
    params.extend([limit, offset])
    cur.execute(
        f"""
        SELECT a.asin, sr.competition_score, sr.demand_score, sr.opportunity_score, sr.scored_at
        FROM scoring_results sr
        JOIN asins a ON a.id = sr.asin_id {where}
        ORDER BY {sort_col} {order_val} NULLS LAST
        LIMIT %s OFFSET %s
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    keys = ["asin", "competition_score", "demand_score", "opportunity_score", "scored_at"]
    data = [dict(zip(keys, [_serialize(v) for v in row])) for row in rows]
    return _envelope(data, total, limit, offset)


def get_saved_views(
    workspace_id: Optional[int] = None,
    limit: int = _LIMIT,
    offset: int = 0,
) -> Dict[str, Any]:
    """Saved research views for workspace. workspace_id required (Step 52 isolation)."""
    if workspace_id is None:
        return _scope_error("workspace_id required", limit, offset)
    raw = list_saved_views(workspace_id)
    total = len(raw)
    slice_ = raw[offset : offset + limit]
    data = [{k: _serialize(v) for k, v in row.items()} for row in slice_]
    return _envelope(data, total, limit, offset)


def get_watchlists(
    workspace_id: Optional[int] = None,
    limit: int = _LIMIT,
    offset: int = 0,
) -> Dict[str, Any]:
    """Watchlists for workspace. workspace_id required (Step 52 isolation)."""
    if workspace_id is None:
        return _scope_error("workspace_id required", limit, offset)
    raw = list_watchlists(workspace_id)
    total = len(raw)
    slice_ = raw[offset : offset + limit]
    data = [{k: _serialize(v) for k, v in row.items()} for row in slice_]
    return _envelope(data, total, limit, offset)


def get_watchlist_items(
    watchlist_id: Optional[int] = None,
    workspace_id: Optional[int] = None,
    limit: int = _LIMIT,
    offset: int = 0,
) -> Dict[str, Any]:
    """Items in a watchlist. workspace_id required when watchlist_id set (Step 52 isolation)."""
    if watchlist_id is None:
        return _scope_error("watchlist_id required", limit, offset)
    if workspace_id is None:
        return _scope_error("workspace_id required", limit, offset)
    wl = get_watchlist(watchlist_id)
    if wl is None or wl.get("workspace_id") != workspace_id:
        return _scope_error("watchlist not in workspace", limit, offset)
    raw = list_watchlist_items(watchlist_id, include_asin=True)
    total = len(raw)
    slice_ = raw[offset : offset + limit]
    data = [{k: _serialize(v) for k, v in row.items()} for row in slice_]
    return _envelope(data, total, limit, offset)


def get_workspace_intelligence_summary_response(
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Step 191/192: Workspace intelligence summary for dashboard/copilot. Returns latest snapshot if available, else computed."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.workspace_intelligence import get_workspace_intelligence_summary_prefer_cached
        summary = get_workspace_intelligence_summary_prefer_cached(workspace_id)
        return {"data": summary, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def post_workspace_intelligence_refresh_response(
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Step 192: Compute and persist workspace intelligence summary (refresh). Returns summary envelope."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.workspace_intelligence import refresh_workspace_intelligence_summary
        summary = refresh_workspace_intelligence_summary(workspace_id)
        return {"data": summary, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_admin_workspace_intelligence_metrics_response() -> Dict[str, Any]:
    """Step 195: Admin workspace intelligence metrics summary. Requires auth; no workspace_id scope."""
    try:
        from amazon_research.workspace_intelligence import get_workspace_intelligence_metrics_summary
        data = get_workspace_intelligence_metrics_summary()
        return {"data": data, "meta": {}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {}}


def get_backend_readiness_response() -> Dict[str, Any]:
    """Step 210: Backend readiness gate. Returns normalized readiness review; no secrets."""
    try:
        from amazon_research.backend_readiness import run_backend_readiness_review
        data = run_backend_readiness_review()
        return {"data": data, "meta": {}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {}}


def get_workspace_dashboard_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 211: Dashboard data serving. Aggregated workspace-scoped payload for dashboard UI."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.dashboard_serving import get_dashboard_payload
        data = get_dashboard_payload(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspace_configuration_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 196: GET workspace configuration (with defaults). workspace_id required."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.workspace_configuration import get_workspace_configuration_with_defaults
        data = get_workspace_configuration_with_defaults(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def put_workspace_configuration_response(workspace_id: Optional[int], body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Step 196: PUT workspace configuration (upsert). Validates and returns updated config."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    if not isinstance(body, dict):
        return {"error": "invalid body", "data": None, "meta": {"workspace_id": workspace_id}}
    try:
        from amazon_research.workspace_configuration import upsert_workspace_configuration, get_workspace_configuration_with_defaults
        upsert_workspace_configuration(workspace_id, body)
        data = get_workspace_configuration_with_defaults(workspace_id)
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(workspace_id, "configuration_updated", source_module="api", event_payload={"updated": True})
        except Exception:
            pass
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspaces_list_response() -> Dict[str, Any]:
    """Step 223: GET /api/workspaces – list all workspaces. Returns { data: [{ id, name, slug, ... }], meta: { count } }."""
    try:
        from amazon_research.db import list_workspaces
        workspaces = list_workspaces()
        out = []
        for w in workspaces:
            row = dict(w)
            for k in ("created_at", "updated_at"):
                if k in row and row[k] is not None and hasattr(row[k], "isoformat"):
                    row[k] = row[k].isoformat()
            out.append(row)
        return {"data": out, "meta": {"count": len(out)}}
    except Exception as e:
        return {"error": str(e), "data": [], "meta": {"count": 0}}


def post_create_workspace_response(body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Step 223: POST /api/workspaces – create workspace. Body: { name (required), description? }. Returns { data: { id, name, slug }, meta } or { error }."""
    if not isinstance(body, dict):
        return {"error": "body must be a json object", "data": None, "meta": {}}
    name = (body.get("name") or "").strip()
    if not name:
        return {"error": "name is required", "data": None, "meta": {}}
    if len(name) > 255:
        return {"error": "name is too long", "data": None, "meta": {}}
    try:
        from amazon_research.db import create_workspace, get_workspace
        workspace_id = create_workspace(name=name)
        ws = get_workspace(workspace_id)
        if not ws:
            return {"error": "workspace created but could not be read", "data": None, "meta": {}}
        data = {"id": ws["id"], "name": ws["name"], "slug": ws["slug"]}
        if ws.get("created_at") and hasattr(ws["created_at"], "isoformat"):
            data["created_at"] = ws["created_at"].isoformat()
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {}}


def get_feature_flags_response() -> Dict[str, Any]:
    """Step 225: GET /api/feature-flags – return current feature flags (env-based). No secrets."""
    try:
        from amazon_research.feature_flags import get_feature_flags
        flags = get_feature_flags()
        return {"data": flags, "meta": {}}
    except Exception as e:
        return {"error": str(e), "data": {}, "meta": {}}


def post_analytics_events_response(body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Step 224: POST /api/analytics/events – record a usage analytics event. Body: { event_name, workspace_id?, metadata? }. Returns { ok } or { error }."""
    if not isinstance(body, dict):
        return {"error": "body must be a json object", "ok": False}
    event_name = (body.get("event_name") or body.get("event") or "").strip()
    if not event_name:
        return {"error": "event_name is required", "ok": False}
    workspace_id = body.get("workspace_id")
    if workspace_id is not None:
        try:
            workspace_id = int(workspace_id)
        except (TypeError, ValueError):
            workspace_id = None
    metadata = body.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        metadata = None
    try:
        from amazon_research.usage_analytics import record_analytics_event
        ok = record_analytics_event(workspace_id=workspace_id, event_name=event_name, metadata=metadata)
        return {"ok": ok}
    except Exception as e:
        return {"error": str(e), "ok": False}


def get_workspace_portfolio_response(
    workspace_id: Optional[int],
    item_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 500,
) -> Dict[str, Any]:
    """Step 197: GET workspace portfolio items (list). Stable { data, meta }."""
    if workspace_id is None:
        return {"data": [], "meta": {"workspace_id": None, "count": 0, "limit": limit}}
    try:
        from amazon_research.db.workspace_portfolio import list_workspace_portfolio_items
        items = list_workspace_portfolio_items(workspace_id, item_type=item_type, status=status, limit=limit)
        # Serialize datetimes for JSON
        out = []
        for it in items:
            row = dict(it)
            for k in ("created_at", "updated_at"):
                if k in row and hasattr(row[k], "isoformat"):
                    row[k] = row[k].isoformat()
            out.append(row)
        if len(out) == 0:
            try:
                from amazon_research.demo_data import should_use_demo_for_portfolio, generate_demo_portfolio_items
                if should_use_demo_for_portfolio(workspace_id, 0):
                    demo_list = generate_demo_portfolio_items(workspace_id)
                    out = []
                    for a in demo_list[:limit]:
                        row = {k: a.get(k) for k in ("id", "workspace_id", "item_type", "item_key", "item_label", "source_type", "status", "created_at", "updated_at") if k in a}
                        if row.get("created_at") and hasattr(row["created_at"], "isoformat"):
                            row["created_at"] = row["created_at"].isoformat()
                        if row.get("updated_at") and hasattr(row["updated_at"], "isoformat"):
                            row["updated_at"] = row["updated_at"].isoformat()
                        out.append(row)
                    return {"data": out, "meta": {"workspace_id": workspace_id, "count": len(out), "limit": limit, "is_demo": True}}
            except Exception:
                pass
        return {"data": out, "meta": {"workspace_id": workspace_id, "count": len(out), "limit": limit}}
    except Exception as e:
        return {"error": str(e), "data": [], "meta": {"workspace_id": workspace_id, "count": 0, "limit": limit}}


def post_workspace_portfolio_response(workspace_id: Optional[int], body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Step 197: POST workspace portfolio item (add). Body: item_type, item_key, item_label?, source_type?, metadata_json?."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    if not isinstance(body, dict):
        return {"error": "invalid body", "data": None, "meta": {"workspace_id": workspace_id}}
    item_type = (body.get("item_type") or "").strip() or None
    item_key = (body.get("item_key") or "").strip() or None
    if not item_key:
        return {"error": "item_key required", "data": None, "meta": {"workspace_id": workspace_id}}
    try:
        from amazon_research.db.workspace_portfolio import add_workspace_portfolio_item, ITEM_TYPES
        ttype = (item_type or "opportunity").strip().lower()
        if ttype not in ITEM_TYPES:
            ttype = "opportunity"
        result = add_workspace_portfolio_item(
            workspace_id,
            item_type=ttype,
            item_key=item_key,
            item_label=body.get("item_label"),
            source_type=body.get("source_type"),
            metadata=body.get("metadata_json") if isinstance(body.get("metadata_json"), dict) else None,
        )
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(workspace_id, "portfolio_item_added", event_label=item_key, source_module="api", event_payload={"item_type": ttype, "item_key": item_key})
        except Exception:
            pass
        return {"data": result, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def patch_workspace_portfolio_archive_response(workspace_id: Optional[int], item_id: Optional[int]) -> Dict[str, Any]:
    """Step 197: PATCH archive portfolio item. Returns { data: { archived: bool }, meta }."""
    if workspace_id is None or item_id is None:
        return {"error": "workspace_id and item_id required", "data": {"archived": False}, "meta": {}}
    try:
        from amazon_research.db.workspace_portfolio import archive_workspace_portfolio_item
        ok = archive_workspace_portfolio_item(workspace_id, item_id)
        if ok:
            try:
                from amazon_research.workspace_activity_log import create_workspace_activity_event
                create_workspace_activity_event(workspace_id, "portfolio_item_archived", source_module="api", event_payload={"item_id": item_id})
            except Exception:
                pass
        return {"data": {"archived": ok}, "meta": {"workspace_id": workspace_id, "item_id": item_id}}
    except Exception as e:
        return {"error": str(e), "data": {"archived": False}, "meta": {"workspace_id": workspace_id, "item_id": item_id}}


def get_workspace_portfolio_summary_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 197: GET workspace portfolio summary. Stable payload."""
    if workspace_id is None:
        return {"data": {"workspace_id": None, "total": 0, "by_type": {}, "by_status": {"active": 0, "archived": 0}}, "meta": {"workspace_id": None}}
    try:
        from amazon_research.db.workspace_portfolio import get_workspace_portfolio_summary
        data = get_workspace_portfolio_summary(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": {"workspace_id": workspace_id, "total": 0, "by_type": {}, "by_status": {"active": 0, "archived": 0}}, "meta": {"workspace_id": workspace_id}}


def get_workspace_activity_response(
    workspace_id: Optional[int],
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Step 199: GET workspace activity events (list). Stable { data, meta }."""
    if workspace_id is None:
        return {"data": [], "meta": {"workspace_id": None, "count": 0, "limit": limit}}
    try:
        from amazon_research.workspace_activity_log import list_workspace_activity_events
        events = list_workspace_activity_events(workspace_id, event_type=event_type, severity=severity, limit=limit)
        out = []
        for ev in events:
            row = dict(ev)
            for k in ("created_at",):
                if k in row and hasattr(row[k], "isoformat"):
                    row[k] = row[k].isoformat()
            out.append(row)
        return {"data": out, "meta": {"workspace_id": workspace_id, "count": len(out), "limit": limit}}
    except Exception as e:
        return {"error": str(e), "data": [], "meta": {"workspace_id": workspace_id, "count": 0, "limit": limit}}


def get_workspace_activity_summary_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 199: GET workspace activity summary. Stable payload."""
    if workspace_id is None:
        return {"data": {"workspace_id": None, "total": 0, "by_event_type": {}, "by_severity": {"info": 0, "warning": 0, "error": 0}}, "meta": {"workspace_id": None}}
    try:
        from amazon_research.workspace_activity_log import get_workspace_activity_summary
        data = get_workspace_activity_summary(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": {"workspace_id": workspace_id, "total": 0, "by_event_type": {}, "by_severity": {"info": 0, "warning": 0, "error": 0}}, "meta": {"workspace_id": workspace_id}}


def get_workspace_alert_preferences_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 198: GET workspace alert preferences (with defaults). Stable payload."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.workspace_alert_preferences import get_workspace_alert_preferences_with_defaults
        data = get_workspace_alert_preferences_with_defaults(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspace_alerts_response(
    workspace_id: Optional[int],
    limit: int = 100,
    alert_type: Optional[str] = None,
    read: Optional[str] = None,
) -> Dict[str, Any]:
    """Step 216: GET workspace alerts (opportunity_alerts). Returns { data: [...], meta } with id, alert_type, severity, title, description, recorded_at, read_at."""
    if workspace_id is None:
        return {"data": [], "meta": {"workspace_id": None, "count": 0}}
    try:
        from amazon_research.db import list_opportunity_alerts
        rows = list_opportunity_alerts(limit=max(1, min(500, limit)), workspace_id=workspace_id)
        out = []
        for r in rows:
            sig = r.get("triggering_signals") or {}
            score = sig.get("score")
            if score is not None:
                try:
                    score = float(score)
                except (TypeError, ValueError):
                    score = None
            if score is not None and score >= 80:
                severity = "high"
            elif score is not None and score >= 60:
                severity = "medium"
            else:
                severity = "low"
            if alert_type and (r.get("alert_type") or "").strip().lower() != (alert_type or "").strip().lower():
                continue
            read_at = r.get("read_at")
            if read == "read" and not read_at:
                continue
            if read == "unread" and read_at:
                continue
            title = (r.get("target_entity") or "").strip() or "Alert"
            reason = (sig.get("reason") or "").strip() or (str(sig)[:200] if sig else "")
            item = {
                "id": r.get("id"),
                "alert_type": r.get("alert_type"),
                "severity": severity,
                "title": title,
                "description": reason,
                "recorded_at": r.get("recorded_at"),
                "read_at": read_at,
            }
            if hasattr(item["recorded_at"], "isoformat"):
                item["recorded_at"] = item["recorded_at"].isoformat()
            if item.get("read_at") and hasattr(item["read_at"], "isoformat"):
                item["read_at"] = item["read_at"].isoformat()
            out.append(item)
        if len(out) == 0:
            try:
                from amazon_research.demo_data import should_use_demo_for_alerts, generate_demo_alerts
                if should_use_demo_for_alerts(workspace_id):
                    demo_list = generate_demo_alerts(workspace_id)
                    out = [{"id": a.get("id"), "alert_type": a.get("alert_type"), "severity": a.get("severity"), "title": a.get("title"), "description": a.get("description"), "recorded_at": a.get("recorded_at"), "read_at": a.get("read_at")} for a in demo_list]
                    return {"data": out, "meta": {"workspace_id": workspace_id, "count": len(out), "is_demo": True}}
            except Exception:
                pass
        return {"data": out, "meta": {"workspace_id": workspace_id, "count": len(out)}}
    except Exception as e:
        return {"error": str(e), "data": [], "meta": {"workspace_id": workspace_id, "count": 0}}


def patch_workspace_alert_read_response(workspace_id: Optional[int], alert_id: Optional[int]) -> Dict[str, Any]:
    """Step 216: PATCH mark alert as read. Returns { data: { read: bool }, meta }."""
    if workspace_id is None or alert_id is None:
        return {"error": "workspace_id and alert_id required", "data": {"read": False}, "meta": {}}
    try:
        from amazon_research.db import set_opportunity_alert_read
        ok = set_opportunity_alert_read(workspace_id, alert_id)
        return {"data": {"read": ok}, "meta": {"workspace_id": workspace_id, "alert_id": alert_id}}
    except Exception as e:
        return {"error": str(e), "data": {"read": False}, "meta": {"workspace_id": workspace_id, "alert_id": alert_id}}


def put_workspace_alert_preferences_response(workspace_id: Optional[int], body: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Step 198: PUT workspace alert preferences (upsert). Validates and returns updated preferences."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    if not isinstance(body, dict):
        return {"error": "invalid body", "data": None, "meta": {"workspace_id": workspace_id}}
    try:
        from amazon_research.workspace_alert_preferences import upsert_workspace_alert_preferences, get_workspace_alert_preferences_with_defaults
        upsert_workspace_alert_preferences(workspace_id, body)
        data = get_workspace_alert_preferences_with_defaults(workspace_id)
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(workspace_id, "alert_preferences_updated", source_module="api", event_payload={"updated": True})
        except Exception:
            pass
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspace_strategy_opportunities_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 201: GET workspace opportunity strategy. Stable payload; computed on read."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.opportunity_strategy import generate_workspace_opportunity_strategy
        data = generate_workspace_opportunity_strategy(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def post_workspace_strategy_opportunities_refresh_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 201: POST refresh workspace opportunity strategy (recompute and optionally log). Returns strategy payload."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.opportunity_strategy import generate_workspace_opportunity_strategy
        data = generate_workspace_opportunity_strategy(workspace_id)
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(
                workspace_id,
                "strategy_refresh",
                event_label="Strategy refresh",
                source_module="api",
                event_payload={"strategy_act_now_count": len(data.get("prioritized_opportunities", [])), "strategy_monitor_count": len(data.get("monitor_opportunities", []))},
            )
        except Exception:
            pass
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspace_portfolio_recommendations_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 202: GET workspace portfolio recommendations. Stable payload; computed on read."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.portfolio_recommendations import generate_workspace_portfolio_recommendations
        data = generate_workspace_portfolio_recommendations(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def post_workspace_portfolio_recommendations_refresh_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 202: POST refresh portfolio recommendations (recompute and log). Returns recommendation payload."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.portfolio_recommendations import generate_workspace_portfolio_recommendations
        data = generate_workspace_portfolio_recommendations(workspace_id)
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(
                workspace_id,
                "portfolio_recommendation_refresh",
                event_label="Portfolio recommendations refresh",
                source_module="api",
                event_payload={"add_count": len(data.get("add_recommendations", [])), "monitor_count": len(data.get("monitor_recommendations", [])), "archive_count": len(data.get("archive_recommendations", []))},
            )
        except Exception:
            pass
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspace_market_entry_signals_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 203: GET workspace market entry signals. Stable payload; computed on read."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.market_entry_signals import generate_workspace_market_entry_signals
        data = generate_workspace_market_entry_signals(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def post_workspace_market_entry_signals_refresh_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 203: POST refresh market entry signals (recompute and log). Returns signals payload."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.market_entry_signals import generate_workspace_market_entry_signals
        data = generate_workspace_market_entry_signals(workspace_id)
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(
                workspace_id,
                "market_entry_signals_refresh",
                event_label="Market entry signals refresh",
                source_module="api",
                event_payload={"enter_now_count": len(data.get("recommended_markets", [])), "monitor_count": len(data.get("monitor_markets", []))},
            )
        except Exception:
            pass
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspace_risk_detection_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 204: GET workspace risk detection. Stable payload; computed on read."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.risk_detection import generate_workspace_risk_detection
        data = generate_workspace_risk_detection(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def post_workspace_risk_detection_refresh_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 204: POST refresh risk detection (recompute and log). Returns risk payload."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.risk_detection import generate_workspace_risk_detection
        data = generate_workspace_risk_detection(workspace_id)
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(
                workspace_id,
                "risk_detection_refresh",
                event_label="Risk detection refresh",
                source_module="api",
                event_payload={"high_count": len(data.get("high_risk_items", [])), "medium_count": len(data.get("medium_risk_items", []))},
            )
        except Exception:
            pass
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def get_workspace_strategic_scores_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 205: GET workspace strategic scores. Stable payload; computed on read."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.strategic_scoring import generate_workspace_strategic_scores
        data = generate_workspace_strategic_scores(workspace_id)
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}


def post_workspace_strategic_scores_refresh_response(workspace_id: Optional[int]) -> Dict[str, Any]:
    """Step 205: POST refresh strategic scores (recompute and log). Returns scoring payload."""
    if workspace_id is None:
        return {"error": "workspace_id required", "data": None, "meta": {}}
    try:
        from amazon_research.strategic_scoring import generate_workspace_strategic_scores
        data = generate_workspace_strategic_scores(workspace_id)
        try:
            from amazon_research.workspace_activity_log import create_workspace_activity_event
            create_workspace_activity_event(
                workspace_id,
                "strategic_scoring_refresh",
                event_label="Strategic scoring refresh",
                source_module="api",
                event_payload={"scored_item_count": len(data.get("scored_items", [])), "top_count": len(data.get("top_scored_items", []))},
            )
        except Exception:
            pass
        return {"data": data, "meta": {"workspace_id": workspace_id}}
    except Exception as e:
        return {"error": str(e), "data": None, "meta": {"workspace_id": workspace_id}}
