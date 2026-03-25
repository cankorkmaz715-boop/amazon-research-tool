#!/usr/bin/env python3
"""Internal read-only API (Step 27). Serves GET /products, /metrics, /scores, /saved_views, /watchlists, /watchlist_items; GET / or /ui or /workflow for workflow UI. Run: python scripts/serve_internal_api.py."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def _parse_query(path: str) -> tuple[str, dict]:
    """Return (path_without_query, query_dict)."""
    if "?" not in path:
        return path, {}
    p, qs = path.split("?", 1)
    out = {}
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return p, out


def _get_headers(handler) -> dict:
    """Read request headers from BaseHTTPRequestHandler."""
    return {k.replace("-", "_").lower(): v for k, v in handler.headers.items()}


def handle_request(path: str, headers: dict = None) -> tuple:
    """Return (status_code, body_dict). Dashboard contract: { data, meta } per endpoint. Step 46: auth + workspace scope."""
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_workspace, record_usage, record_audit, record_billable_event, check_quota
    from amazon_research.api import get_workspaces_list_response, get_feature_flags_response, get_products, get_metrics, get_scores, get_saved_views, get_watchlists, get_watchlist_items, get_workspace_intelligence_summary_response, post_workspace_intelligence_refresh_response, get_admin_workspace_intelligence_metrics_response, get_backend_readiness_response, get_workspace_dashboard_response, get_workspace_configuration_response, get_workspace_portfolio_response, get_workspace_portfolio_summary_response, get_workspace_alert_preferences_response, get_workspace_alerts_response, get_workspace_activity_response, get_workspace_activity_summary_response, get_workspace_strategy_opportunities_response, get_workspace_portfolio_recommendations_response, get_workspace_market_entry_signals_response, get_workspace_risk_detection_response, get_workspace_strategic_scores_response
    from amazon_research.auth import validate_internal_request
    from amazon_research.rate_limit import check_rate_limit, record_rate_limit, get_effective_rate_limit
    from amazon_research.decision_hardening import (
        check_decision_read_allowed,
        record_decision_read,
        check_decision_refresh_allowed,
        record_decision_refresh,
        PATH_INTELLIGENCE_REFRESH,
        PATH_STRATEGY_REFRESH,
        PATH_PORTFOLIO_RECOMMENDATIONS_REFRESH,
        PATH_MARKET_ENTRY_REFRESH,
        PATH_RISK_DETECTION_REFRESH,
        PATH_STRATEGIC_SCORES_REFRESH,
    )
    init_db()
    headers = headers or {}
    allowed, workspace_id = validate_internal_request(headers=headers)
    if not allowed:
        return 401, {"error": "unauthorized"}
    path_only, q = _parse_query(path)
    limit = int(q.get("limit", 500))
    offset = int(q.get("offset", 0))
    sort_by = q.get("sort_by") or None
    order = q.get("order", "desc")
    limit = max(1, min(1000, limit))
    offset = max(0, offset)
    ws_id = workspace_id
    if ws_id is None and q.get("workspace_id"):
        try:
            ws_id = int(q.get("workspace_id"))
        except (TypeError, ValueError):
            ws_id = None
    # Step 223: GET /api/workspaces – list workspaces (no workspace_id required)
    if path_only == "/api/workspaces" or path_only == "/api/workspaces/":
        body = get_workspaces_list_response()
        return (200, body) if not body.get("error") else (500, body)

    # Step 225: GET /api/feature-flags – feature flags (no workspace_id required)
    if path_only == "/api/feature-flags" or path_only == "/api/feature-flags/":
        body = get_feature_flags_response()
        return (200, body) if not body.get("error") else (500, body)

    # Step 52: workspace-scoped endpoints require valid workspace_id
    _scoped_paths = ("/products", "/products/", "/metrics", "/metrics/", "/scores", "/scores/",
                     "/saved_views", "/saved_views/", "/watchlists", "/watchlists/", "/watchlist_items", "/watchlist_items/")
    if path_only in _scoped_paths:
        if ws_id is None:
            return 403, {"error": "workspace_id required"}
        if get_workspace(ws_id) is None:
            return 403, {"error": "invalid workspace_id"}
        # Step 57/60: rate limit API per workspace; limit from plan or config
        api_limit = get_effective_rate_limit(ws_id, "api")
        allowed, retry_after = check_rate_limit(ws_id, "api", api_limit, 60.0)
        if not allowed:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
    def _quota_block(quota_type: str):
        r = check_quota(ws_id, quota_type)
        if not r.get("allowed") and r.get("limit") is not None:
            record_audit(ws_id, "quota_exceeded", {"quota_type": quota_type, "limit": r["limit"], "used": r["used"]})
            record_billable_event(ws_id, "quota_overage", {"quota_type": quota_type, "limit": r["limit"], "used": r["used"]})
            return True, (403, {"error": "quota exceeded", "quota_type": quota_type, "limit": r["limit"], "used": r["used"], "remaining": r["remaining"]})
        return False, None

    kw = dict(limit=limit, offset=offset, sort_by=sort_by, order=order, workspace_id=ws_id)
    if path_only == "/products" or path_only == "/products/":
        blocked, resp = _quota_block("api_products")
        if blocked:
            return resp
        body = get_products(**kw, category=q.get("category"))
        if not body.get("error"):
            record_usage(ws_id, "api_products")
            record_audit(ws_id, "api_products")
            record_billable_event(ws_id, "api_request", {"endpoint": "products"})
            record_rate_limit(ws_id, "api")
        return (403, body) if body.get("error") else (200, body)
    if path_only == "/metrics" or path_only == "/metrics/":
        blocked, resp = _quota_block("api_metrics")
        if blocked:
            return resp
        body = get_metrics(**kw, asin=q.get("asin"))
        if not body.get("error"):
            record_usage(ws_id, "api_metrics")
            record_audit(ws_id, "api_metrics")
            record_billable_event(ws_id, "api_request", {"endpoint": "metrics"})
            record_rate_limit(ws_id, "api")
        return (403, body) if body.get("error") else (200, body)
    if path_only == "/scores" or path_only == "/scores/":
        blocked, resp = _quota_block("api_scores")
        if blocked:
            return resp
        body = get_scores(**kw, asin=q.get("asin"))
        if not body.get("error"):
            record_usage(ws_id, "api_scores")
            record_audit(ws_id, "api_scores")
            record_billable_event(ws_id, "api_request", {"endpoint": "scores"})
            record_rate_limit(ws_id, "api")
        return (403, body) if body.get("error") else (200, body)
    if path_only == "/saved_views" or path_only == "/saved_views/":
        blocked, resp = _quota_block("api_saved_views")
        if blocked:
            return resp
        record_usage(ws_id, "api_saved_views")
        record_audit(ws_id, "api_saved_views")
        record_billable_event(ws_id, "api_request", {"endpoint": "saved_views"})
        record_rate_limit(ws_id, "api")
        return 200, get_saved_views(workspace_id=ws_id, limit=limit, offset=offset)
    if path_only == "/watchlists" or path_only == "/watchlists/":
        blocked, resp = _quota_block("api_watchlists")
        if blocked:
            return resp
        record_usage(ws_id, "api_watchlists")
        record_audit(ws_id, "api_watchlists")
        record_billable_event(ws_id, "api_request", {"endpoint": "watchlists"})
        record_rate_limit(ws_id, "api")
        return 200, get_watchlists(workspace_id=ws_id, limit=limit, offset=offset)
    if path_only == "/watchlist_items" or path_only == "/watchlist_items/":
        blocked, resp = _quota_block("api_watchlist_items")
        if blocked:
            return resp
        wlid = q.get("watchlist_id")
        try:
            wlid = int(wlid) if wlid else None
        except (TypeError, ValueError):
            wlid = None
        body = get_watchlist_items(watchlist_id=wlid, workspace_id=ws_id, limit=limit, offset=offset)
        if not body.get("error"):
            record_usage(ws_id, "api_watchlist_items")
            record_audit(ws_id, "api_watchlist_items")
            record_billable_event(ws_id, "api_request", {"endpoint": "watchlist_items"})
            record_rate_limit(ws_id, "api")
        return (403, body) if body.get("error") else (200, body)

    # Step 191: GET /api/workspaces/:workspaceId/intelligence/summary
    if path_only.startswith("/api/workspaces/") and path_only.endswith("/intelligence/summary"):
        parts = path_only.rstrip("/").split("/")
        # ["", "api", "workspaces", "<id>", "intelligence", "summary"]
        ws_id_from_path = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_from_path = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_from_path is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_from_path) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_from_path, "api")
        allowed, retry_after = check_rate_limit(ws_id_from_path, "api", api_limit, 60.0)
        if not allowed:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_dr, retry_dr = check_decision_read_allowed(ws_id_from_path)
            if not allowed_dr:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_dr or 60}
        except Exception:
            pass
        body = get_workspace_intelligence_summary_response(workspace_id=ws_id_from_path)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_from_path, "api_products")
        record_audit(ws_id_from_path, "api_workspace_intelligence_summary")
        record_billable_event(ws_id_from_path, "api_request", {"endpoint": "workspace_intelligence_summary"})
        record_rate_limit(ws_id_from_path, "api")
        try:
            record_decision_read(ws_id_from_path)
        except Exception:
            pass
        return 200, body

    # Step 211: GET /api/workspaces/:workspaceId/dashboard and /dashboard/summary
    if path_only.startswith("/api/workspaces/") and ("/dashboard" in path_only):
        parts = path_only.rstrip("/").split("/")
        ws_id_dash = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_dash = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_dash is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_dash) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_dash, "api")
        allowed_dash, retry_after = check_rate_limit(ws_id_dash, "api", api_limit, 60.0)
        if not allowed_dash:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_dr, retry_dr = check_decision_read_allowed(ws_id_dash)
            if not allowed_dr:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_dr or 60}
        except Exception:
            pass
        body = get_workspace_dashboard_response(workspace_id=ws_id_dash)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_dash, "api_products")
        record_rate_limit(ws_id_dash, "api")
        try:
            record_decision_read(ws_id_dash)
        except Exception:
            pass
        return 200, body

    # Step 195: GET /api/admin/intelligence/workspace/metrics
    if path_only == "/api/admin/intelligence/workspace/metrics" or path_only == "/api/admin/intelligence/workspace/metrics/":
        body = get_admin_workspace_intelligence_metrics_response()
        if body.get("error"):
            return 500, body
        return 200, body

    # Step 210: GET /api/admin/backend/readiness
    if path_only == "/api/admin/backend/readiness" or path_only == "/api/admin/backend/readiness/":
        body = get_backend_readiness_response()
        if body.get("error"):
            return 500, body
        return 200, body

    # Step 196: GET /api/workspaces/:workspaceId/configuration
    if path_only.startswith("/api/workspaces/") and (path_only.endswith("/configuration") or path_only.endswith("/configuration/")):
        parts = path_only.rstrip("/").split("/")
        ws_id_cfg = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_cfg = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_cfg is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_cfg) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_cfg, "api")
        allowed_cfg, retry_after = check_rate_limit(ws_id_cfg, "api", api_limit, 60.0)
        if not allowed_cfg:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        body = get_workspace_configuration_response(workspace_id=ws_id_cfg)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_cfg, "api_products")
        record_rate_limit(ws_id_cfg, "api")
        return 200, body

    # Step 197: GET /api/workspaces/:workspaceId/portfolio/summary
    if path_only.startswith("/api/workspaces/") and "/portfolio/summary" in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_pf = None
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and "portfolio" in parts and "summary" in parts:
            try:
                ws_id_pf = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_pf is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_pf) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_pf, "api")
        allowed_pf, retry_after = check_rate_limit(ws_id_pf, "api", api_limit, 60.0)
        if not allowed_pf:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        body = get_workspace_portfolio_summary_response(workspace_id=ws_id_pf)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_pf, "api_products")
        record_rate_limit(ws_id_pf, "api")
        return 200, body

    # Step 197: GET /api/workspaces/:workspaceId/portfolio
    if path_only.startswith("/api/workspaces/") and (path_only.endswith("/portfolio") or path_only.endswith("/portfolio/")):
        parts = path_only.rstrip("/").split("/")
        ws_id_pf = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_pf = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_pf is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_pf) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_pf, "api")
        allowed_pf, retry_after = check_rate_limit(ws_id_pf, "api", api_limit, 60.0)
        if not allowed_pf:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        body = get_workspace_portfolio_response(workspace_id=ws_id_pf, item_type=q.get("item_type"), status=q.get("status"), limit=limit)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_pf, "api_products")
        record_rate_limit(ws_id_pf, "api")
        return 200, body

    # Step 199: GET /api/workspaces/:workspaceId/activity/summary
    if path_only.startswith("/api/workspaces/") and "/activity/summary" in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_act = None
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and "activity" in parts and "summary" in parts:
            try:
                ws_id_act = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_act is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_act) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_act, "api")
        allowed_act, retry_after = check_rate_limit(ws_id_act, "api", api_limit, 60.0)
        if not allowed_act:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        body = get_workspace_activity_summary_response(workspace_id=ws_id_act)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_act, "api_products")
        record_rate_limit(ws_id_act, "api")
        return 200, body

    # Step 199: GET /api/workspaces/:workspaceId/activity
    if path_only.startswith("/api/workspaces/") and (path_only.endswith("/activity") or path_only.endswith("/activity/")):
        parts = path_only.rstrip("/").split("/")
        ws_id_act = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_act = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_act is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_act) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_act, "api")
        allowed_act, retry_after = check_rate_limit(ws_id_act, "api", api_limit, 60.0)
        if not allowed_act:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        body = get_workspace_activity_response(workspace_id=ws_id_act, event_type=q.get("event_type"), severity=q.get("severity"), limit=limit)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_act, "api_products")
        record_rate_limit(ws_id_act, "api")
        return 200, body

    # Step 203: GET /api/workspaces/:workspaceId/strategy/market-entry-signals
    if path_only.startswith("/api/workspaces/") and "/strategy/market-entry-signals" in path_only and "/refresh" not in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_me = None
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "market-entry-signals" in path_only:
            try:
                ws_id_me = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_me is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_me) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_me, "api")
        allowed_me, retry_after = check_rate_limit(ws_id_me, "api", api_limit, 60.0)
        if not allowed_me:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_dr, retry_dr = check_decision_read_allowed(ws_id_me)
            if not allowed_dr:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_dr or 60}
        except Exception:
            pass
        body = get_workspace_market_entry_signals_response(workspace_id=ws_id_me)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_me, "api_products")
        record_rate_limit(ws_id_me, "api")
        try:
            record_decision_read(ws_id_me)
        except Exception:
            pass
        return 200, body

    # Step 204: GET /api/workspaces/:workspaceId/strategy/risk-detection
    if path_only.startswith("/api/workspaces/") and "/strategy/risk-detection" in path_only and "/refresh" not in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_rd = None
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "risk-detection" in path_only:
            try:
                ws_id_rd = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_rd is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_rd) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_rd, "api")
        allowed_rd, retry_after = check_rate_limit(ws_id_rd, "api", api_limit, 60.0)
        if not allowed_rd:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_dr, retry_dr = check_decision_read_allowed(ws_id_rd)
            if not allowed_dr:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_dr or 60}
        except Exception:
            pass
        body = get_workspace_risk_detection_response(workspace_id=ws_id_rd)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_rd, "api_products")
        record_rate_limit(ws_id_rd, "api")
        try:
            record_decision_read(ws_id_rd)
        except Exception:
            pass
        return 200, body

    # Step 205: GET /api/workspaces/:workspaceId/strategy/strategic-scores
    if path_only.startswith("/api/workspaces/") and "/strategy/strategic-scores" in path_only and "/refresh" not in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_ss = None
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "strategic-scores" in path_only:
            try:
                ws_id_ss = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_ss is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_ss) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_ss, "api")
        allowed_ss, retry_after = check_rate_limit(ws_id_ss, "api", api_limit, 60.0)
        if not allowed_ss:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_dr, retry_dr = check_decision_read_allowed(ws_id_ss)
            if not allowed_dr:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_dr or 60}
        except Exception:
            pass
        body = get_workspace_strategic_scores_response(workspace_id=ws_id_ss)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_ss, "api_products")
        record_rate_limit(ws_id_ss, "api")
        try:
            record_decision_read(ws_id_ss)
        except Exception:
            pass
        return 200, body

    # Step 202: GET /api/workspaces/:workspaceId/strategy/portfolio-recommendations
    if path_only.startswith("/api/workspaces/") and "/strategy/portfolio-recommendations" in path_only and "/refresh" not in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_rec = None
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "portfolio-recommendations" in path_only:
            try:
                ws_id_rec = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_rec is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_rec) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_rec, "api")
        allowed_rec, retry_after = check_rate_limit(ws_id_rec, "api", api_limit, 60.0)
        if not allowed_rec:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_dr, retry_dr = check_decision_read_allowed(ws_id_rec)
            if not allowed_dr:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_dr or 60}
        except Exception:
            pass
        body = get_workspace_portfolio_recommendations_response(workspace_id=ws_id_rec)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_rec, "api_products")
        record_rate_limit(ws_id_rec, "api")
        try:
            record_decision_read(ws_id_rec)
        except Exception:
            pass
        return 200, body

    # Step 201: GET /api/workspaces/:workspaceId/strategy/opportunities
    if path_only.startswith("/api/workspaces/") and "/strategy/opportunities" in path_only and "/refresh" not in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_st = None
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "opportunities" in parts:
            try:
                ws_id_st = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_st is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_st) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_st, "api")
        allowed_st, retry_after = check_rate_limit(ws_id_st, "api", api_limit, 60.0)
        if not allowed_st:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_dr, retry_dr = check_decision_read_allowed(ws_id_st)
            if not allowed_dr:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_dr or 60}
        except Exception:
            pass
        body = get_workspace_strategy_opportunities_response(workspace_id=ws_id_st)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_st, "api_products")
        record_rate_limit(ws_id_st, "api")
        try:
            record_decision_read(ws_id_st)
        except Exception:
            pass
        return 200, body

    # Step 216: GET /api/workspaces/:workspaceId/alerts
    if path_only.startswith("/api/workspaces/") and ("/alerts" in path_only and "/alert-preferences" not in path_only):
        parts = path_only.rstrip("/").split("/")
        if len(parts) >= 5 and parts[1] == "api" and parts[2] == "workspaces" and parts[4] == "alerts":
            try:
                ws_id_al = int(parts[3])
            except (ValueError, TypeError):
                ws_id_al = None
            if ws_id_al is not None and get_workspace(ws_id_al) is not None:
                limit = max(1, min(500, int(q.get("limit", 100))))
                body = get_workspace_alerts_response(workspace_id=ws_id_al, limit=limit, alert_type=q.get("alert_type"), read=q.get("read"))
                if body.get("error"):
                    return 403, body
                record_usage(ws_id_al, "api_products")
                record_rate_limit(ws_id_al, "api")
                return 200, body
            if ws_id_al is not None:
                return 403, {"error": "invalid workspace_id"}

    # Step 198: GET /api/workspaces/:workspaceId/alert-preferences
    if path_only.startswith("/api/workspaces/") and (path_only.endswith("/alert-preferences") or path_only.endswith("/alert-preferences/")):
        parts = path_only.rstrip("/").split("/")
        ws_id_ap = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_ap = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_ap is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_ap) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_ap, "api")
        allowed_ap, retry_after = check_rate_limit(ws_id_ap, "api", api_limit, 60.0)
        if not allowed_ap:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        body = get_workspace_alert_preferences_response(workspace_id=ws_id_ap)
        if body.get("error"):
            return 403, body
        record_usage(ws_id_ap, "api_products")
        record_rate_limit(ws_id_ap, "api")
        return 200, body

    return 404, {"error": "not found"}


def handle_put_request(path: str, body_bytes: bytes, headers: dict = None) -> tuple:
    """PUT: Step 196 configuration; Step 198 alert-preferences."""
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_workspace, record_usage
    from amazon_research.api import put_workspace_configuration_response, put_workspace_alert_preferences_response
    from amazon_research.auth import validate_internal_request
    from amazon_research.rate_limit import check_rate_limit, record_rate_limit, get_effective_rate_limit
    init_db()
    headers = headers or {}
    allowed, _ = validate_internal_request(headers=headers)
    if not allowed:
        return 401, {"error": "unauthorized"}
    path_only, _ = _parse_query(path)
    if not path_only.startswith("/api/workspaces/"):
        return 404, {"error": "not found"}
    parts = path_only.rstrip("/").split("/")
    ws_id_put = None
    if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
        try:
            ws_id_put = int(parts[3])
        except (ValueError, TypeError):
            pass
    if ws_id_put is None:
        return 400, {"error": "invalid workspace id in path"}
    if get_workspace(ws_id_put) is None:
        return 403, {"error": "invalid workspace_id"}
    api_limit = get_effective_rate_limit(ws_id_put, "api")
    allowed_put, retry_after = check_rate_limit(ws_id_put, "api", api_limit, 60.0)
    if not allowed_put:
        return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
    body_obj = {}
    if body_bytes:
        try:
            body_obj = json.loads(body_bytes.decode("utf-8"))
        except Exception as e:
            return 400, {"error": "invalid json", "detail": str(e)}
    if not isinstance(body_obj, dict):
        return 400, {"error": "body must be a json object"}
    # Step 198: PUT /api/workspaces/:workspaceId/alert-preferences
    if path_only.endswith("/alert-preferences") or path_only.endswith("/alert-preferences/"):
        resp = put_workspace_alert_preferences_response(workspace_id=ws_id_put, body=body_obj)
    else:
        # Step 196: PUT /api/workspaces/:workspaceId/configuration
        if not (path_only.endswith("/configuration") or path_only.endswith("/configuration/")):
            return 404, {"error": "not found"}
        resp = put_workspace_configuration_response(workspace_id=ws_id_put, body=body_obj)
    if resp.get("error"):
        return 400, resp
    record_usage(ws_id_put, "api_products")
    record_rate_limit(ws_id_put, "api")
    return 200, resp


def handle_post_request(path: str, body_bytes: bytes = None, headers: dict = None) -> tuple:
    """POST: Step 192 intelligence/refresh; Step 197 portfolio add; Step 201 strategy/opportunities/refresh."""
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_workspace, record_usage, record_audit, record_billable_event
    from amazon_research.api import post_workspace_intelligence_refresh_response, post_workspace_portfolio_response, post_workspace_strategy_opportunities_refresh_response, post_workspace_portfolio_recommendations_refresh_response, post_workspace_market_entry_signals_refresh_response, post_workspace_risk_detection_refresh_response, post_workspace_strategic_scores_refresh_response
    from amazon_research.auth import validate_internal_request
    from amazon_research.rate_limit import check_rate_limit, record_rate_limit, get_effective_rate_limit
    from amazon_research.decision_hardening import (
        check_decision_refresh_allowed,
        record_decision_refresh,
        PATH_INTELLIGENCE_REFRESH,
        PATH_STRATEGY_REFRESH,
        PATH_PORTFOLIO_RECOMMENDATIONS_REFRESH,
        PATH_MARKET_ENTRY_REFRESH,
        PATH_RISK_DETECTION_REFRESH,
        PATH_STRATEGIC_SCORES_REFRESH,
    )
    init_db()
    headers = headers or {}
    allowed, _ = validate_internal_request(headers=headers)
    if not allowed:
        return 401, {"error": "unauthorized"}
    path_only, _ = _parse_query(path)

    # Step 223: POST /api/workspaces – create workspace (no workspace_id in path)
    if path_only == "/api/workspaces" or path_only == "/api/workspaces/":
        body_obj = {}
        if body_bytes:
            try:
                body_obj = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                return 400, {"error": "invalid json", "detail": str(e)}
        if not isinstance(body_obj, dict):
            return 400, {"error": "body must be a json object"}
        from amazon_research.api import post_create_workspace_response
        resp = post_create_workspace_response(body_obj)
        if resp.get("error"):
            return 400, resp
        return 201, resp

    # Step 224: POST /api/analytics/events – usage analytics (no workspace in path)
    if path_only == "/api/analytics/events" or path_only == "/api/analytics/events/":
        body_obj = {}
        if body_bytes:
            try:
                body_obj = json.loads(body_bytes.decode("utf-8"))
            except Exception as e:
                return 400, {"error": "invalid json", "detail": str(e)}
        if not isinstance(body_obj, dict):
            return 400, {"error": "body must be a json object"}
        from amazon_research.api import post_analytics_events_response
        resp = post_analytics_events_response(body_obj)
        if resp.get("error"):
            return 400, resp
        return 200, resp

    # Step 203: POST /api/workspaces/:workspaceId/strategy/market-entry-signals/refresh
    if path_only.startswith("/api/workspaces/") and "/strategy/market-entry-signals/refresh" in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_mes = None
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "market-entry-signals" in path_only and "refresh" in path_only:
            try:
                ws_id_mes = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_mes is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_mes) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_mes, "api")
        allowed_mes, retry_after = check_rate_limit(ws_id_mes, "api", api_limit, 60.0)
        if not allowed_mes:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_ref, retry_ref, _ = check_decision_refresh_allowed(ws_id_mes, PATH_MARKET_ENTRY_REFRESH)
            if not allowed_ref:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_ref or 60}
        except Exception:
            pass
        body = post_workspace_market_entry_signals_refresh_response(workspace_id=ws_id_mes)
        if body.get("error"):
            return 403, body
        try:
            record_decision_refresh(ws_id_mes, PATH_MARKET_ENTRY_REFRESH)
        except Exception:
            pass
        record_usage(ws_id_mes, "api_products")
        record_rate_limit(ws_id_mes, "api")
        return 200, body

    # Step 204: POST /api/workspaces/:workspaceId/strategy/risk-detection/refresh
    if path_only.startswith("/api/workspaces/") and "/strategy/risk-detection/refresh" in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_rd = None
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "risk-detection" in path_only and "refresh" in path_only:
            try:
                ws_id_rd = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_rd is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_rd) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_rd, "api")
        allowed_rd, retry_after = check_rate_limit(ws_id_rd, "api", api_limit, 60.0)
        if not allowed_rd:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_ref, retry_ref, _ = check_decision_refresh_allowed(ws_id_rd, PATH_RISK_DETECTION_REFRESH)
            if not allowed_ref:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_ref or 60}
        except Exception:
            pass
        body = post_workspace_risk_detection_refresh_response(workspace_id=ws_id_rd)
        if body.get("error"):
            return 403, body
        try:
            record_decision_refresh(ws_id_rd, PATH_RISK_DETECTION_REFRESH)
        except Exception:
            pass
        record_usage(ws_id_rd, "api_products")
        record_rate_limit(ws_id_rd, "api")
        return 200, body

    # Step 205: POST /api/workspaces/:workspaceId/strategy/strategic-scores/refresh
    if path_only.startswith("/api/workspaces/") and "/strategy/strategic-scores/refresh" in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_ss = None
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "strategic-scores" in path_only and "refresh" in path_only:
            try:
                ws_id_ss = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_ss is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_ss) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_ss, "api")
        allowed_ss, retry_after = check_rate_limit(ws_id_ss, "api", api_limit, 60.0)
        if not allowed_ss:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_ref, retry_ref, _ = check_decision_refresh_allowed(ws_id_ss, PATH_STRATEGIC_SCORES_REFRESH)
            if not allowed_ref:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_ref or 60}
        except Exception:
            pass
        body = post_workspace_strategic_scores_refresh_response(workspace_id=ws_id_ss)
        if body.get("error"):
            return 403, body
        try:
            record_decision_refresh(ws_id_ss, PATH_STRATEGIC_SCORES_REFRESH)
        except Exception:
            pass
        record_usage(ws_id_ss, "api_products")
        record_rate_limit(ws_id_ss, "api")
        return 200, body

    # Step 202: POST /api/workspaces/:workspaceId/strategy/portfolio-recommendations/refresh
    if path_only.startswith("/api/workspaces/") and "/strategy/portfolio-recommendations/refresh" in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_prec = None
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "portfolio-recommendations" in path_only and "refresh" in path_only:
            try:
                ws_id_prec = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_prec is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_prec) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_prec, "api")
        allowed_prec, retry_after = check_rate_limit(ws_id_prec, "api", api_limit, 60.0)
        if not allowed_prec:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_ref, retry_ref, _ = check_decision_refresh_allowed(ws_id_prec, PATH_PORTFOLIO_RECOMMENDATIONS_REFRESH)
            if not allowed_ref:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_ref or 60}
        except Exception:
            pass
        body = post_workspace_portfolio_recommendations_refresh_response(workspace_id=ws_id_prec)
        if body.get("error"):
            return 403, body
        try:
            record_decision_refresh(ws_id_prec, PATH_PORTFOLIO_RECOMMENDATIONS_REFRESH)
        except Exception:
            pass
        record_usage(ws_id_prec, "api_products")
        record_rate_limit(ws_id_prec, "api")
        return 200, body

    # Step 201: POST /api/workspaces/:workspaceId/strategy/opportunities/refresh
    if path_only.startswith("/api/workspaces/") and "/strategy/opportunities/refresh" in path_only:
        parts = path_only.rstrip("/").split("/")
        ws_id_str = None
        if len(parts) >= 6 and parts[1] == "api" and parts[2] == "workspaces" and "strategy" in parts and "opportunities" in parts and "refresh" in parts:
            try:
                ws_id_str = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_str is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_str) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_str, "api")
        allowed_str, retry_after = check_rate_limit(ws_id_str, "api", api_limit, 60.0)
        if not allowed_str:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_ref, retry_ref, _ = check_decision_refresh_allowed(ws_id_str, PATH_STRATEGY_REFRESH)
            if not allowed_ref:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_ref or 60}
        except Exception:
            pass
        body = post_workspace_strategy_opportunities_refresh_response(workspace_id=ws_id_str)
        if body.get("error"):
            return 403, body
        try:
            record_decision_refresh(ws_id_str, PATH_STRATEGY_REFRESH)
        except Exception:
            pass
        record_usage(ws_id_str, "api_products")
        record_rate_limit(ws_id_str, "api")
        return 200, body

    # Step 197: POST /api/workspaces/:workspaceId/portfolio
    if path_only.rstrip("/").endswith("/portfolio") and "/portfolio/" not in path_only.replace("/portfolio", ""):
        parts = path_only.rstrip("/").split("/")
        ws_id_p = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_p = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_p is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_p) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_p, "api")
        allowed_rl, retry_after = check_rate_limit(ws_id_p, "api", api_limit, 60.0)
        if not allowed_rl:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        body_obj = {}
        if body_bytes:
            try:
                body_obj = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body_obj = {}
        if not isinstance(body_obj, dict):
            body_obj = {}
        body = post_workspace_portfolio_response(workspace_id=ws_id_p, body=body_obj)
        if body.get("error"):
            return 400, body
        record_usage(ws_id_p, "api_products")
        record_rate_limit(ws_id_p, "api")
        return 201, body

    # Step 192: POST /api/workspaces/:workspaceId/intelligence/refresh
    if path_only.startswith("/api/workspaces/") and path_only.endswith("/intelligence/refresh"):
        parts = path_only.rstrip("/").split("/")
        ws_id_from_path = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "workspaces":
            try:
                ws_id_from_path = int(parts[3])
            except (ValueError, TypeError):
                pass
        if ws_id_from_path is None:
            return 400, {"error": "invalid workspace id in path"}
        if get_workspace(ws_id_from_path) is None:
            return 403, {"error": "invalid workspace_id"}
        api_limit = get_effective_rate_limit(ws_id_from_path, "api")
        allowed_rl, retry_after = check_rate_limit(ws_id_from_path, "api", api_limit, 60.0)
        if not allowed_rl:
            return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
        try:
            allowed_ref, retry_ref, _ = check_decision_refresh_allowed(ws_id_from_path, PATH_INTELLIGENCE_REFRESH)
            if not allowed_ref:
                return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_ref or 60}
        except Exception:
            pass
        body = post_workspace_intelligence_refresh_response(workspace_id=ws_id_from_path)
        if body.get("error"):
            return 403, body
        try:
            record_decision_refresh(ws_id_from_path, PATH_INTELLIGENCE_REFRESH)
        except Exception:
            pass
        record_usage(ws_id_from_path, "api_products")
        record_audit(ws_id_from_path, "api_workspace_intelligence_refresh")
        record_billable_event(ws_id_from_path, "api_request", {"endpoint": "workspace_intelligence_refresh"})
        record_rate_limit(ws_id_from_path, "api")
        return 200, body

    return 404, {"error": "not found"}


def handle_patch_request(path: str, headers: dict = None) -> tuple:
    """Step 197: PATCH /api/workspaces/:workspaceId/portfolio/:itemId/archive. Step 216: PATCH .../alerts/:alertId/read."""
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_workspace, record_usage
    from amazon_research.api import patch_workspace_portfolio_archive_response, patch_workspace_alert_read_response
    from amazon_research.auth import validate_internal_request
    from amazon_research.rate_limit import check_rate_limit, record_rate_limit, get_effective_rate_limit
    init_db()
    headers = headers or {}
    allowed, _ = validate_internal_request(headers=headers)
    if not allowed:
        return 401, {"error": "unauthorized"}
    path_only, _ = _parse_query(path)
    parts = path_only.rstrip("/").split("/")

    # Step 216: PATCH /api/workspaces/:workspaceId/alerts/:alertId/read
    if path_only.startswith("/api/workspaces/") and "/alerts/" in path_only and "/read" in path_only and len(parts) >= 7 and parts[1] == "api" and parts[2] == "workspaces" and parts[4] == "alerts" and parts[6] == "read":
        try:
            ws_id_ar = int(parts[3])
            alert_id_ar = int(parts[5])
        except (ValueError, TypeError):
            ws_id_ar = alert_id_ar = None
        if ws_id_ar is not None and alert_id_ar is not None and get_workspace(ws_id_ar) is not None:
            body = patch_workspace_alert_read_response(workspace_id=ws_id_ar, alert_id=alert_id_ar)
            record_usage(ws_id_ar, "api_products")
            record_rate_limit(ws_id_ar, "api")
            return 200, body
        if ws_id_ar is not None or alert_id_ar is not None:
            return 400, {"error": "invalid workspace id or alert id in path"}

    # .../portfolio/123/archive or .../portfolio/123/archive/
    if not path_only.startswith("/api/workspaces/") or "/portfolio/" not in path_only or "/archive" not in path_only:
        return 404, {"error": "not found"}
    # ["", "api", "workspaces", "<ws_id>", "portfolio", "<item_id>", "archive"]
    ws_id_patch = None
    item_id_patch = None
    if len(parts) >= 7 and parts[1] == "api" and parts[2] == "workspaces" and parts[4] == "portfolio" and parts[6] == "archive":
        try:
            ws_id_patch = int(parts[3])
            item_id_patch = int(parts[5])
        except (ValueError, TypeError):
            pass
    if ws_id_patch is None or item_id_patch is None:
        return 400, {"error": "invalid workspace id or item id in path"}
    if get_workspace(ws_id_patch) is None:
        return 403, {"error": "invalid workspace_id"}
    api_limit = get_effective_rate_limit(ws_id_patch, "api")
    allowed_rl, retry_after = check_rate_limit(ws_id_patch, "api", api_limit, 60.0)
    if not allowed_rl:
        return 429, {"error": "rate_limit_exceeded", "retry_after_seconds": retry_after or 60}
    body = patch_workspace_portfolio_archive_response(workspace_id=ws_id_patch, item_id=item_id_patch)
    if body.get("error"):
        return 400, body
    record_usage(ws_id_patch, "api_products")
    record_rate_limit(ws_id_patch, "api")
    return 200, body


def _serve_workspace_shared_css(handler) -> bool:
    """Step 219: Serve shared workspace dashboard CSS for polish/consistency. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/internal_ui/workspace-shared.css", "/internal_ui/workspace-shared.css/"):
        return False
    css_path = os.path.join(ROOT, "internal_ui", "workspace-shared.css")
    if not os.path.isfile(css_path):
        return False
    with open(css_path, "rb") as f:
        css = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/css; charset=utf-8")
    handler.send_header("Content-Length", len(css))
    handler.end_headers()
    handler.wfile.write(css)
    return True


def _serve_workspace_feature_flags_js(handler) -> bool:
    """Step 225: Serve workspace feature flags script. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/internal_ui/workspace-feature-flags.js", "/internal_ui/workspace-feature-flags.js/"):
        return False
    js_path = os.path.join(ROOT, "internal_ui", "workspace-feature-flags.js")
    if not os.path.isfile(js_path):
        return False
    with open(js_path, "rb") as f:
        js = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "application/javascript; charset=utf-8")
    handler.send_header("Content-Length", len(js))
    handler.end_headers()
    handler.wfile.write(js)
    return True


def _serve_workspace_analytics_js(handler) -> bool:
    """Step 224: Serve workspace analytics tracker script. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/internal_ui/workspace-analytics.js", "/internal_ui/workspace-analytics.js/"):
        return False
    js_path = os.path.join(ROOT, "internal_ui", "workspace-analytics.js")
    if not os.path.isfile(js_path):
        return False
    with open(js_path, "rb") as f:
        js = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "application/javascript; charset=utf-8")
    handler.send_header("Content-Length", len(js))
    handler.end_headers()
    handler.wfile.write(js)
    return True


def _serve_workflow_ui(handler) -> bool:
    """Serve workflow UI HTML if path is / or /ui or /workflow. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/", "/ui", "/workflow", "/workflow/"):
        return False
    ui_path = os.path.join(ROOT, "internal_ui", "workflow.html")
    if not os.path.isfile(ui_path):
        return False
    with open(ui_path, "rb") as f:
        html = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(html))
    handler.end_headers()
    handler.wfile.write(html)
    return True


def _serve_workspace_overview_ui(handler) -> bool:
    """Step 212: Serve workspace overview dashboard HTML if path is /workspace-overview or /dashboard. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/workspace-overview", "/workspace-overview/", "/dashboard", "/dashboard/"):
        return False
    ui_path = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
    if not os.path.isfile(ui_path):
        return False
    with open(ui_path, "rb") as f:
        html = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(html))
    handler.end_headers()
    handler.wfile.write(html)
    return True


def _serve_alert_center_ui(handler) -> bool:
    """Step 216: Serve alert center HTML if path is /alert-center. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/alert-center", "/alert-center/"):
        return False
    ui_path = os.path.join(ROOT, "internal_ui", "alert-center.html")
    if not os.path.isfile(ui_path):
        return False
    with open(ui_path, "rb") as f:
        html = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(html))
    handler.end_headers()
    handler.wfile.write(html)
    return True


def _serve_workspace_preferences_ui(handler) -> bool:
    """Step 227: Serve workspace preferences page at /workspace-preferences. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/workspace-preferences", "/workspace-preferences/"):
        return False
    ui_path = os.path.join(ROOT, "internal_ui", "workspace-preferences.html")
    if not os.path.isfile(ui_path):
        return False
    with open(ui_path, "rb") as f:
        html = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(html))
    handler.end_headers()
    handler.wfile.write(html)
    return True


def _serve_settings_ui(handler) -> bool:
    """Step 226: Serve SaaS settings page at /settings. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/settings", "/settings/"):
        return False
    ui_path = os.path.join(ROOT, "internal_ui", "settings.html")
    if not os.path.isfile(ui_path):
        return False
    with open(ui_path, "rb") as f:
        html = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(html))
    handler.end_headers()
    handler.wfile.write(html)
    return True


def _serve_workspace_creation_ui(handler) -> bool:
    """Step 223: Serve workspace creation page at /create-workspace or /workspace-create. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/create-workspace", "/create-workspace/", "/workspace-create", "/workspace-create/"):
        return False
    ui_path = os.path.join(ROOT, "internal_ui", "workspace-creation.html")
    if not os.path.isfile(ui_path):
        return False
    with open(ui_path, "rb") as f:
        html = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(html))
    handler.end_headers()
    handler.wfile.write(html)
    return True


def _serve_portfolio_ui(handler) -> bool:
    """Step 215: Serve portfolio management HTML if path is /portfolio or /portfolio-management. Returns True if served."""
    path_only, _ = _parse_query(handler.path)
    if path_only not in ("/portfolio", "/portfolio/", "/portfolio-management", "/portfolio-management/"):
        return False
    ui_path = os.path.join(ROOT, "internal_ui", "portfolio.html")
    if not os.path.isfile(ui_path):
        return False
    with open(ui_path, "rb") as f:
        html = f.read()
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", len(html))
    handler.end_headers()
    handler.wfile.write(html)
    return True


def _handle_export_get(handler) -> bool:
    """Step 228: Handle GET /api/workspaces/:id/export/dashboard|opportunities|portfolio|alerts. Returns True if handled."""
    path_only, q = _parse_query(handler.path)
    if "/export/" not in path_only or not path_only.startswith("/api/workspaces/"):
        return False
    parts = path_only.rstrip("/").split("/")
    # /api/workspaces/123/export/dashboard -> parts: ["", "api", "workspaces", "123", "export", "dashboard"]
    if len(parts) < 6 or parts[1] != "api" or parts[2] != "workspaces" or parts[4] != "export":
        return False
    try:
        ws_id = int(parts[3])
    except (ValueError, TypeError):
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": "invalid workspace id in path"}).encode("utf-8"))
        return True
    export_type = (parts[5] or "").strip().lower()
    if export_type not in ("dashboard", "opportunities", "portfolio", "alerts"):
        handler.send_response(400)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": "invalid export type"}).encode("utf-8"))
        return True
    fmt = (q.get("format") or "json").strip().lower()
    if fmt not in ("json", "csv"):
        fmt = "json"
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.db import init_db, get_workspace, record_usage
    from amazon_research.auth import validate_internal_request
    from amazon_research.export_report import get_export_dashboard, get_export_opportunities, get_export_portfolio, get_export_alerts
    init_db()
    headers = {k: v for k, v in handler.headers.items()}
    allowed, _ = validate_internal_request(headers=headers)
    if not allowed:
        handler.send_response(401)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": "unauthorized"}).encode("utf-8"))
        return True
    if get_workspace(ws_id) is None:
        handler.send_response(403)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": "invalid workspace_id"}).encode("utf-8"))
        return True
    try:
        if export_type == "dashboard":
            payload, csv_str, content_type = get_export_dashboard(ws_id, fmt)
        elif export_type == "opportunities":
            payload, csv_str, content_type = get_export_opportunities(ws_id, fmt)
        elif export_type == "portfolio":
            payload, csv_str, content_type = get_export_portfolio(ws_id, fmt)
        else:
            payload, csv_str, content_type = get_export_alerts(ws_id, fmt)
    except Exception as e:
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        return True
    if payload is None:
        handler.send_response(403)
        handler.send_header("Content-Type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps({"error": "export failed"}).encode("utf-8"))
        return True
    try:
        record_usage(ws_id, "api_products")
    except Exception:
        pass
    filename = "workspace-{}-{}.{}".format(ws_id, export_type, "csv" if csv_str else "json")
    disposition = 'attachment; filename="{}"'.format(filename.replace('"', "%22"))
    handler.send_response(200)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Disposition", disposition)
    if csv_str is not None:
        body_bytes = csv_str.encode("utf-8")
    else:
        body_bytes = json.dumps(payload).encode("utf-8")
    handler.send_header("Content-Length", len(body_bytes))
    handler.end_headers()
    handler.wfile.write(body_bytes)
    return True


class APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if _serve_workspace_shared_css(self):
                return
            if _serve_workspace_feature_flags_js(self):
                return
            if _serve_workspace_analytics_js(self):
                return
            if _serve_workflow_ui(self):
                return
            if _serve_workspace_overview_ui(self):
                return
            if _serve_portfolio_ui(self):
                return
            if _serve_alert_center_ui(self):
                return
            if _serve_workspace_creation_ui(self):
                return
            if _serve_settings_ui(self):
                return
            if _serve_workspace_preferences_ui(self):
                return
            if _handle_export_get(self):
                return
            headers = {k: v for k, v in self.headers.items()}
            status, body = handle_request(self.path, headers=headers)
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def do_POST(self):
        try:
            headers = {k: v for k, v in self.headers.items()}
            body_bytes = b""
            if self.headers.get("Content-Length"):
                try:
                    n = int(self.headers.get("Content-Length", 0))
                    if 0 < n <= 1024 * 1024:
                        body_bytes = self.rfile.read(n)
                except (ValueError, TypeError):
                    pass
            status, body = handle_post_request(self.path, body_bytes=body_bytes, headers=headers)
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def do_PATCH(self):
        try:
            headers = {k: v for k, v in self.headers.items()}
            status, body = handle_patch_request(self.path, headers=headers)
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def do_PUT(self):
        try:
            headers = {k: v for k, v in self.headers.items()}
            length = int(self.headers.get("Content-Length", 0) or 0)
            body_bytes = self.rfile.read(length) if length else b""
            status, body = handle_put_request(self.path, body_bytes, headers=headers)
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from amazon_research.deployment_hardening import validate_required_env, get_bind_host, get_bind_port
        errors = validate_required_env()
        if errors:
            for msg in errors:
                print(msg, file=sys.stderr)
            sys.exit(1)
        host, port = get_bind_host(), get_bind_port()
    except ImportError:
        host, port = "0.0.0.0", int(os.environ.get("INTERNAL_API_PORT", "8766"))
    with HTTPServer((host, port), APIHandler) as httpd:
        print(f"Internal API http://{host}:{port}  /  /ui  /workflow  /workspace-overview  /dashboard  /portfolio  /alert-center  /products  ...")
        httpd.serve_forever()
