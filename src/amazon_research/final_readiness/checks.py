"""
Step 230: Final readiness checks – deployment, UI, export, feature flags, demo, startup.
Deterministic; each check returns one item; never raises.
"""
import os
from typing import Any, Dict, List

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
    try:
        import importlib
        m = importlib.import_module(module_path)
        if attr:
            getattr(m, attr)
        return True, None
    except Exception as e:
        return False, str(e)


def _project_root() -> str:
    # __file__ is .../src/amazon_research/final_readiness/checks.py -> go up to repo root
    here = os.path.abspath(os.path.dirname(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(here, "scripts")) and os.path.isdir(os.path.join(here, "internal_ui")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def run_final_checks() -> List[Dict[str, Any]]:
    """Run final-specific checks (deploy, UI, export, feature flags, demo). Never raises."""
    results: List[Dict[str, Any]] = []
    root = _project_root()

    # Deployment hardening
    ok, err = _safe_import("amazon_research.deployment_hardening", "validate_required_env")
    if ok:
        results.append(_item("deployment_hardening_env", "Env validation (deployment hardening)", PASS, SEVERITY_LOW, "Env validation available."))
    else:
        results.append(_item("deployment_hardening_env", "Env validation (deployment hardening)", FAIL, SEVERITY_MEDIUM, "Deployment hardening module missing.", err or "import_failed", "Add deployment_hardening or run startup_sanity_check."))

    ok, err = _safe_import("amazon_research.deployment_hardening", "get_bind_port")
    if ok:
        results.append(_item("deployment_hardening_port", "Port config (proxy readiness)", PASS, SEVERITY_LOW, "Port config available."))
    else:
        results.append(_item("deployment_hardening_port", "Port config (proxy readiness)", WARNING, SEVERITY_LOW, "Port config optional.", err or "import_failed"))

    # Startup sanity script exists
    sanity_script = os.path.join(root, "scripts", "startup_sanity_check.py")
    if os.path.isfile(sanity_script):
        results.append(_item("startup_sanity_script", "Startup sanity script", PASS, SEVERITY_LOW, "startup_sanity_check.py present."))
    else:
        results.append(_item("startup_sanity_script", "Startup sanity script", WARNING, SEVERITY_LOW, "Startup sanity script not found.", "file_missing"))

    # Export / report layer
    ok, err = _safe_import("amazon_research.export_report", "get_export_dashboard")
    if ok:
        results.append(_item("export_report_available", "Export / report layer", PASS, SEVERITY_LOW, "Export report module available."))
    else:
        results.append(_item("export_report_available", "Export / report layer", WARNING, SEVERITY_LOW, "Export report optional.", err or "import_failed"))

    # Feature flags
    ok, err = _safe_import("amazon_research.feature_flags", "is_feature_enabled")
    if ok:
        results.append(_item("feature_flags_available", "Feature flags", PASS, SEVERITY_LOW, "Feature flags module available."))
    else:
        results.append(_item("feature_flags_available", "Feature flags", WARNING, SEVERITY_LOW, "Feature flags optional.", err or "import_failed"))

    # Demo data (safe demo mode)
    ok, err = _safe_import("amazon_research.demo_data", "should_use_demo_for_dashboard")
    if ok:
        results.append(_item("demo_data_available", "Demo mode safety", PASS, SEVERITY_LOW, "Demo data module available; demo gated."))
    else:
        results.append(_item("demo_data_available", "Demo mode safety", WARNING, SEVERITY_LOW, "Demo data optional.", err or "import_failed"))

    # Dashboard serving
    ok, err = _safe_import("amazon_research.dashboard_serving.aggregation", "get_dashboard_payload")
    if ok:
        results.append(_item("dashboard_serving_available", "Dashboard data serving", PASS, SEVERITY_LOW, "Dashboard aggregation available."))
    else:
        results.append(_item("dashboard_serving_available", "Dashboard data serving", FAIL, SEVERITY_MEDIUM, "Dashboard serving missing.", err or "import_failed"))

    # UI routes / files presence (structural check only)
    internal_ui = os.path.join(root, "internal_ui")
    key_pages = ["workspace-overview.html", "portfolio.html", "alert-center.html", "settings.html", "workspace-preferences.html", "workspace-creation.html"]
    missing = [p for p in key_pages if not os.path.isfile(os.path.join(internal_ui, p))]
    if not missing:
        results.append(_item("ui_pages_present", "UI route files (overview, portfolio, alerts, settings, prefs, creation)", PASS, SEVERITY_LOW, "Key UI pages present."))
    else:
        results.append(_item("ui_pages_present", "UI route files", WARNING, SEVERITY_LOW, f"Missing UI files: {missing[:5]}.", ",".join(missing)))

    # Serve script wires export and deployment
    serve_path = os.path.join(root, "scripts", "serve_internal_api.py")
    if os.path.isfile(serve_path):
        with open(serve_path, "r", encoding="utf-8") as f:
            serve_content = f.read()
        if "validate_required_env" in serve_content and "_handle_export_get" in serve_content:
            results.append(_item("serve_wiring", "API server (env + export wiring)", PASS, SEVERITY_LOW, "Serve script wires env validation and export."))
        elif "_handle_export_get" in serve_content:
            results.append(_item("serve_wiring", "API server wiring", WARNING, SEVERITY_LOW, "Export wired; env validation not in serve.", "optional"))
        else:
            results.append(_item("serve_wiring", "API server wiring", WARNING, SEVERITY_LOW, "Export or env validation wiring unclear.", "check_serve_internal_api"))
    else:
        results.append(_item("serve_wiring", "API server", FAIL, SEVERITY_MEDIUM, "serve_internal_api.py not found.", "file_missing"))

    # Workspace isolation (already in backend checks; duplicate for final checklist)
    ok, err = _safe_import("amazon_research.workspace_isolation", "require_workspace_context")
    if ok:
        results.append(_item("final_isolation_safety", "Workspace isolation safety", PASS, SEVERITY_HIGH, "Isolation guards present."))
    else:
        results.append(_item("final_isolation_safety", "Workspace isolation safety", FAIL, SEVERITY_CRITICAL, "Isolation module missing.", err or "import_failed"))

    return results
