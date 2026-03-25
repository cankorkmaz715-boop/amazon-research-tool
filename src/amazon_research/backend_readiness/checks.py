"""
Step 210: Backend readiness checks – deterministic, rule-based checks per subsystem.
Each check returns a single item dict; never raises.
"""
from typing import Any, Dict, List

from amazon_research.logging_config import get_logger

logger = get_logger("backend_readiness.checks")

PASS = "pass"
WARNING = "warning"
FAIL = "fail"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"
SEVERITY_CRITICAL = "critical"


def _item(
    check_key: str,
    check_label: str,
    status: str,
    severity: str,
    rationale: str,
    evidence: str = "",
    recommended_action: str = "",
) -> Dict[str, Any]:
    return {
        "check_key": check_key,
        "check_label": check_label,
        "status": status,
        "severity": severity,
        "rationale": rationale,
        "evidence": evidence or "",
        "recommended_action": recommended_action or "",
    }


def _safe_import(module_path: str, attr: str = None) -> tuple:
    """Try import; return (True, None) or (False, error_message)."""
    try:
        import importlib
        m = importlib.import_module(module_path)
        if attr:
            getattr(m, attr)
        return True, None
    except Exception as e:
        return False, str(e)


def run_all_checks() -> List[Dict[str, Any]]:
    """Run all readiness checks. Never raises; returns list of check items."""
    results: List[Dict[str, Any]] = []

    # Workspace intelligence foundation
    ok, err = _safe_import("amazon_research.workspace_intelligence", "get_workspace_intelligence_summary_prefer_cached")
    if ok:
        results.append(_item("workspace_intelligence_available", "Workspace intelligence foundation", PASS, SEVERITY_LOW, "Module importable and key function present.", "import_ok"))
    else:
        results.append(_item("workspace_intelligence_available", "Workspace intelligence foundation", FAIL, SEVERITY_HIGH, "Workspace intelligence module or API missing.", err or "import_failed", "Verify workspace_intelligence package and exports."))

    # Persistence layer
    ok, err = _safe_import("amazon_research.db.workspace_intelligence_snapshots", "get_latest_workspace_intelligence_snapshot")
    if ok:
        results.append(_item("persistence_layer_available", "Persistence layer (snapshots)", PASS, SEVERITY_LOW, "Snapshot persistence module available."))
    else:
        results.append(_item("persistence_layer_available", "Persistence layer (snapshots)", FAIL, SEVERITY_MEDIUM, "Snapshot persistence module missing.", err or "import_failed"))

    # Cache layer
    ok, err = _safe_import("amazon_research.workspace_intelligence.cache", "get_cached_summary")
    if ok:
        results.append(_item("cache_layer_available", "Cache layer", PASS, SEVERITY_LOW, "Cache module available."))
    else:
        results.append(_item("cache_layer_available", "Cache layer", WARNING, SEVERITY_LOW, "Cache module optional.", err or "import_failed"))

    # Metrics layer
    ok, err = _safe_import("amazon_research.workspace_intelligence.metrics", "get_workspace_intelligence_metrics_summary")
    if ok:
        results.append(_item("metrics_layer_available", "Metrics layer", PASS, SEVERITY_LOW, "Metrics module available."))
    else:
        results.append(_item("metrics_layer_available", "Metrics layer", WARNING, SEVERITY_LOW, "Metrics module optional.", err or "import_failed"))

    # Workspace configuration
    ok, err = _safe_import("amazon_research.workspace_configuration", "get_workspace_configuration_with_defaults")
    if ok:
        results.append(_item("workspace_configuration_available", "Workspace configuration", PASS, SEVERITY_LOW, "Configuration layer available."))
    else:
        results.append(_item("workspace_configuration_available", "Workspace configuration", FAIL, SEVERITY_MEDIUM, "Configuration module missing.", err or "import_failed"))

    # Portfolio tracking
    ok, err = _safe_import("amazon_research.workspace_portfolio", "list_workspace_portfolio_items")
    if ok:
        results.append(_item("portfolio_tracking_available", "Portfolio tracking", PASS, SEVERITY_LOW, "Portfolio module available."))
    else:
        results.append(_item("portfolio_tracking_available", "Portfolio tracking", FAIL, SEVERITY_MEDIUM, "Portfolio module missing.", err or "import_failed"))

    # Alert preferences
    ok, err = _safe_import("amazon_research.workspace_alert_preferences", "get_effective_alert_settings")
    if ok:
        results.append(_item("alert_preferences_available", "Alert preferences", PASS, SEVERITY_LOW, "Alert preferences module available."))
    else:
        results.append(_item("alert_preferences_available", "Alert preferences", FAIL, SEVERITY_MEDIUM, "Alert preferences module missing.", err or "import_failed"))

    # Activity log
    ok, err = _safe_import("amazon_research.workspace_activity_log", "create_workspace_activity_event")
    if ok:
        results.append(_item("activity_log_available", "Activity log", PASS, SEVERITY_LOW, "Activity log module available."))
    else:
        results.append(_item("activity_log_available", "Activity log", WARNING, SEVERITY_LOW, "Activity log optional.", err or "import_failed"))

    # Multi-workspace isolation
    ok, err = _safe_import("amazon_research.workspace_isolation", "require_workspace_context")
    if ok:
        results.append(_item("isolation_available", "Multi-workspace isolation", PASS, SEVERITY_HIGH, "Isolation guards available."))
    else:
        results.append(_item("isolation_available", "Multi-workspace isolation", FAIL, SEVERITY_CRITICAL, "Isolation module missing.", err or "import_failed"))

    # Strategy engine
    ok, err = _safe_import("amazon_research.opportunity_strategy", "generate_workspace_opportunity_strategy")
    if ok:
        results.append(_item("strategy_engine_available", "Opportunity strategy engine", PASS, SEVERITY_LOW, "Strategy module available."))
    else:
        results.append(_item("strategy_engine_available", "Opportunity strategy engine", FAIL, SEVERITY_MEDIUM, "Strategy module missing.", err or "import_failed"))

    # Portfolio recommendations
    ok, err = _safe_import("amazon_research.portfolio_recommendations", "generate_workspace_portfolio_recommendations")
    if ok:
        results.append(_item("recommendation_engine_available", "Portfolio recommendation engine", PASS, SEVERITY_LOW, "Recommendation module available."))
    else:
        results.append(_item("recommendation_engine_available", "Portfolio recommendation engine", FAIL, SEVERITY_MEDIUM, "Recommendation module missing.", err or "import_failed"))

    # Market entry signals
    ok, err = _safe_import("amazon_research.market_entry_signals", "generate_workspace_market_entry_signals")
    if ok:
        results.append(_item("market_entry_available", "Market entry signals engine", PASS, SEVERITY_LOW, "Market entry module available."))
    else:
        results.append(_item("market_entry_available", "Market entry signals engine", FAIL, SEVERITY_MEDIUM, "Market entry module missing.", err or "import_failed"))

    # Risk detection
    ok, err = _safe_import("amazon_research.risk_detection", "generate_workspace_risk_detection")
    if ok:
        results.append(_item("risk_detection_available", "Risk detection engine", PASS, SEVERITY_LOW, "Risk detection module available."))
    else:
        results.append(_item("risk_detection_available", "Risk detection engine", FAIL, SEVERITY_MEDIUM, "Risk detection module missing.", err or "import_failed"))

    # Strategic scoring
    ok, err = _safe_import("amazon_research.strategic_scoring", "generate_workspace_strategic_scores")
    if ok:
        results.append(_item("strategic_scoring_available", "Strategic scoring layer", PASS, SEVERITY_LOW, "Strategic scoring module available."))
    else:
        results.append(_item("strategic_scoring_available", "Strategic scoring layer", FAIL, SEVERITY_MEDIUM, "Strategic scoring module missing.", err or "import_failed"))

    # Decision hardening / rate limiting
    ok, err = _safe_import("amazon_research.decision_hardening", "check_decision_read_allowed")
    if ok:
        results.append(_item("decision_hardening_available", "Decision hardening / rate limiting", PASS, SEVERITY_LOW, "Decision hardening module available."))
    else:
        results.append(_item("decision_hardening_available", "Decision hardening / rate limiting", FAIL, SEVERITY_MEDIUM, "Decision hardening module missing.", err or "import_failed"))

    # Worker stabilization
    ok, err = _safe_import("amazon_research.worker_stability", "execute_with_stability")
    if ok:
        results.append(_item("worker_stability_available", "Worker stabilization / queue safety", PASS, SEVERITY_LOW, "Worker stability module available."))
    else:
        results.append(_item("worker_stability_available", "Worker stabilization / queue safety", FAIL, SEVERITY_MEDIUM, "Worker stability module missing.", err or "import_failed"))

    # Resource guard
    ok, err = _safe_import("amazon_research.resource_guard", "check_resource_guard")
    if ok:
        results.append(_item("resource_guard_available", "Memory and resource guard", PASS, SEVERITY_LOW, "Resource guard module available."))
    else:
        results.append(_item("resource_guard_available", "Memory and resource guard", FAIL, SEVERITY_MEDIUM, "Resource guard module missing.", err or "import_failed"))

    # Error recovery / failsafe
    ok, err = _safe_import("amazon_research.error_recovery", "run_with_failsafe")
    if ok:
        results.append(_item("error_recovery_available", "Error recovery / failsafe", PASS, SEVERITY_LOW, "Error recovery module available."))
    else:
        results.append(_item("error_recovery_available", "Error recovery / failsafe", FAIL, SEVERITY_MEDIUM, "Error recovery module missing.", err or "import_failed"))

    # Payload stability: workspace intelligence summary returns expected keys (optional call)
    try:
        from amazon_research.workspace_intelligence import get_workspace_intelligence_summary
        summary = get_workspace_intelligence_summary(99999)
        if isinstance(summary, dict) and "workspace_id" in summary:
            results.append(_item("payload_stability_intelligence", "Payload stability (intelligence)", PASS, SEVERITY_LOW, "Summary returns stable shape.", "keys_present"))
        else:
            results.append(_item("payload_stability_intelligence", "Payload stability (intelligence)", WARNING, SEVERITY_LOW, "Summary shape incomplete or empty.", "empty_or_missing_keys"))
    except Exception as e:
        results.append(_item("payload_stability_intelligence", "Payload stability (intelligence)", WARNING, SEVERITY_LOW, "Summary call failed (e.g. DB not init).", str(e)[:200]))

    # Fallback / recovery sanity
    try:
        from amazon_research.error_recovery import stable_failure_response
        out = stable_failure_response(1, "test")
        if isinstance(out, dict) and "ok" in out and "error" in out:
            results.append(_item("recovery_fallback_sanity", "Recovery fallback sanity", PASS, SEVERITY_LOW, "Stable failure response shape present."))
        else:
            results.append(_item("recovery_fallback_sanity", "Recovery fallback sanity", WARNING, SEVERITY_LOW, "Unexpected fallback shape.", "shape_mismatch"))
    except Exception as e:
        results.append(_item("recovery_fallback_sanity", "Recovery fallback sanity", FAIL, SEVERITY_MEDIUM, "Error recovery API missing.", str(e)[:200]))

    # Scheduler integration (refresh runner importable)
    ok, err = _safe_import("amazon_research.workspace_intelligence.refresh_runner", "run_refresh_for_workspaces")
    if ok:
        results.append(_item("scheduler_integration_sanity", "Scheduler integration sanity", PASS, SEVERITY_LOW, "Refresh runner available."))
    else:
        results.append(_item("scheduler_integration_sanity", "Scheduler integration sanity", WARNING, SEVERITY_LOW, "Refresh runner optional.", err or "import_failed"))

    return results
