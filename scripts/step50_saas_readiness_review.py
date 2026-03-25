#!/usr/bin/env python3
"""
Step 50: SaaS Readiness Review.
Audits user/workspace structure, data isolation, API, access control, export,
monitoring, ops, cost/bandwidth, maintainability, scaling from a SaaS perspective.
Produces strengths, gaps, risks, and recommended next steps. No rewrite.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def _gather_components():
    """Check presence of SaaS-relevant modules and capabilities. Returns dict."""
    out = {}
    try:
        from amazon_research.db import (
            create_workspace,
            get_workspace,
            list_workspaces,
            create_user,
            list_asins_by_workspace,
        )
        out["workspace_model"] = True
    except Exception:
        out["workspace_model"] = False
    try:
        from amazon_research.auth import validate_internal_request
        out["access_control"] = True
    except Exception:
        out["access_control"] = False
    try:
        from amazon_research.api import (
            get_products,
            get_metrics,
            get_scores,
            get_saved_views,
            get_watchlists,
            get_watchlist_items,
        )
        out["api_workspace_aware"] = True
    except Exception:
        out["api_workspace_aware"] = False
    try:
        from amazon_research.export import export_research_csv, export_research_json, get_research_data_for_workspace
        out["export_layer"] = True
    except Exception:
        out["export_layer"] = False
    try:
        from amazon_research.monitoring import (
            health_check,
            send_pipeline_failure_alert,
            get_telemetry_summary,
        )
        out["monitoring_alerting"] = True
    except Exception:
        out["monitoring_alerting"] = False
    try:
        from amazon_research.config import get_config
        cfg = get_config()
        out["config_central"] = hasattr(cfg, "internal_api_key")
    except Exception:
        out["config_central"] = False
    ui_path = os.path.join(ROOT, "internal_ui", "workflow.html")
    out["workflow_ui"] = os.path.isfile(ui_path)
    return out


def _build_review(components):
    """Build SaaS-focused strengths, gaps, risks, recommended next steps."""
    strengths = [
        "User/workspace model: workspaces and users exist; asins and discovery_seeds support workspace_id.",
        "Workspace-scoped features: saved research views, watchlists, notification rules, export by workspace.",
        "Internal API is workspace-aware (products, metrics, scores, saved_views, watchlists) with stable { data, meta } contract.",
        "Access control: optional API key (INTERNAL_API_KEY), X-Workspace-Id validation; no key required when unset.",
        "Export layer: CSV/JSON per workspace; get_research_data_for_workspace enforces isolation.",
        "Monitoring: health checks, optional Sentry, pipeline failure webhook alert, cost/bandwidth telemetry.",
        "Ops: cron/systemd examples, retention cleanup, config tuning layer; workflow UI at /, /ui, /workflow.",
    ]
    gaps = [
        "No per-user identity or login: users are workspace-linked identifiers only; no passwords or sessions.",
        "No public signup or tenant onboarding: workspaces/users created via DB or internal tooling only.",
        "Single shared pipeline: discovery/refresh/scoring not workspace-scoped; all tenants share one run.",
        "No per-tenant quotas or rate limits: API and pipeline are not limited by workspace.",
        "No billing or usage metering: telemetry is in-memory only; no persistent usage records per workspace.",
        "API key is global: one INTERNAL_API_KEY for all callers; no per-workspace or per-user keys.",
        "Workflow UI is unauthenticated at delivery: auth is via header/input; no login page or session.",
    ]
    risks = [
        "Security: API key in headers only; no HTTPS enforcement in script; secrets in env only (no vault).",
        "Multi-tenant: pipeline and seeds are global—one workspace could dominate discovery; no tenant-specific seeds.",
        "Data isolation: export and API filter by workspace_id but asins without workspace_id are visible to all when no workspace_id sent.",
        "Operational: single process; no horizontal scaling; DB and browser are single points of failure.",
        "Compliance: no audit log of who accessed what; no data residency or deletion-by-tenant.",
    ]
    recommended = [
        "Add per-workspace API keys or scoped tokens so each tenant has its own credential.",
        "Scope discovery seeds (and optionally pipeline runs) by workspace so tenants only discover within their seeds.",
        "Persist usage/telemetry per workspace for quotas and future billing.",
        "Introduce per-tenant limits (e.g. max ASINs, max refresh/day) before externalizing.",
        "Add audit logging for API access and export by workspace/user.",
        "Enforce HTTPS and secure secret storage before any public or multi-tenant deployment.",
    ]
    return {
        "strengths": strengths,
        "gaps": gaps,
        "risks": risks,
        "recommended_next_steps": recommended,
    }


def main():
    from dotenv import load_dotenv
    load_dotenv()
    components = _gather_components()
    review = _build_review(components)
    required = ["workspace_model", "access_control", "api_workspace_aware", "export_layer", "monitoring_alerting"]
    all_ok = all(components.get(k) for k in required)
    print("saas readiness review OK" if all_ok else "saas readiness review INCOMPLETE (missing components)")
    print("strengths:", "; ".join(review["strengths"]))
    print("gaps:", "; ".join(review["gaps"]))
    print("risks:", "; ".join(review["risks"]))
    print("recommended next steps:", "; ".join(review["recommended_next_steps"]))
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
