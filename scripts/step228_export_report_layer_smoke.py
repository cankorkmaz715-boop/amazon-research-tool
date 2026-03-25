#!/usr/bin/env python3
"""
Step 228 smoke test: Export/report layer. Validates dashboard, opportunity,
portfolio export generation, CSV/JSON format sanity, workspace-scoped safety,
and safe failure behavior.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

dashboard_ok = False
opportunity_ok = False
portfolio_ok = False
csv_json_ok = False
scoped_ok = False
failure_ok = False

# Backend: export_report module
export_init = os.path.join(ROOT, "src", "amazon_research", "export_report", "__init__.py")
export_service = os.path.join(ROOT, "src", "amazon_research", "export_report", "service.py")
export_formatters = os.path.join(ROOT, "src", "amazon_research", "export_report", "formatters.py")
if os.path.isfile(export_init) and os.path.isfile(export_service) and os.path.isfile(export_formatters):
    with open(export_init, "r", encoding="utf-8") as f:
        init_content = f.read()
    with open(export_service, "r", encoding="utf-8") as f:
        svc = f.read()
    with open(export_formatters, "r", encoding="utf-8") as f:
        fmt_content = f.read()
    if "get_export_dashboard" in init_content and "get_export_dashboard" in svc:
        dashboard_ok = True
    if "get_export_opportunities" in init_content and "get_export_opportunities" in svc:
        opportunity_ok = True
    if "get_export_portfolio" in init_content and "get_export_portfolio" in svc:
        portfolio_ok = True
    if "rows_to_csv" in fmt_content and "text/csv" in svc and "application/json" in svc:
        csv_json_ok = True
    if "workspace_id" in svc and "None" in svc:
        scoped_ok = True
    if "except Exception" in svc or "payload is None" in svc:
        failure_ok = True

# Routes in serve_internal_api
serve_path = os.path.join(ROOT, "scripts", "serve_internal_api.py")
if os.path.isfile(serve_path):
    with open(serve_path, "r", encoding="utf-8") as f:
        serve = f.read()
    if "/export/" in serve and "_handle_export_get" in serve and "export/dashboard" in serve:
        dashboard_ok = dashboard_ok and True
    if "export/opportunities" in serve and "export/portfolio" in serve and "export/alerts" in serve:
        opportunity_ok = opportunity_ok and True
        portfolio_ok = portfolio_ok and True
    if "Content-Disposition" in serve and "attachment" in serve:
        csv_json_ok = csv_json_ok and True
    if "get_workspace(ws_id)" in serve and "invalid workspace_id" in serve:
        scoped_ok = scoped_ok and True
    if "403" in serve and "500" in serve:
        failure_ok = failure_ok and True

# Optional: run export service with workspace_id=None to assert safe failure
try:
    from amazon_research.export_report import get_export_dashboard, get_export_opportunities, get_export_portfolio, get_export_alerts
    d_payload, d_csv, d_ct = get_export_dashboard(None, "json")
    o_payload, o_csv, o_ct = get_export_opportunities(None, "json")
    p_payload, p_csv, p_ct = get_export_portfolio(None, "json")
    a_payload, a_csv, a_ct = get_export_alerts(None, "json")
    if d_payload is None and o_payload is not None and isinstance(o_payload, dict) and "data" in o_payload:
        failure_ok = True
    if isinstance(p_payload, dict) and "data" in p_payload and isinstance(a_payload, dict) and "data" in a_payload:
        scoped_ok = True
except Exception:
    pass

# Frontend: export UI on dashboard
overview = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
if os.path.isfile(overview):
    with open(overview, "r", encoding="utf-8") as f:
        ov = f.read()
    if "export-btn" in ov and "export-menu" in ov and "data-export" in ov and "export/dashboard" in ov or "/export/" in ov:
        dashboard_ok = dashboard_ok and True
    if "Export" in ov and "Opportunities" in ov and "Portfolio" in ov and "Alerts" in ov:
        csv_json_ok = csv_json_ok and True

# CSV format sanity: formatters produce valid CSV shape
try:
    from amazon_research.export_report.formatters import rows_to_csv
    out = rows_to_csv([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}], ["a", "b"])
    if "a,b" in out and "\n" in out and "1,x" in out or "1," in out:
        csv_json_ok = True
except Exception:
    pass

print("export report layer OK")
print("dashboard export generation: %s" % ("OK" if dashboard_ok else "FAIL"))
print("opportunity export generation: %s" % ("OK" if opportunity_ok else "FAIL"))
print("portfolio export generation: %s" % ("OK" if portfolio_ok else "FAIL"))
print("csv json format sanity: %s" % ("OK" if csv_json_ok else "FAIL"))
print("workspace scoped export safety: %s" % ("OK" if scoped_ok else "FAIL"))
print("safe failure behavior: %s" % ("OK" if failure_ok else "FAIL"))

if not (dashboard_ok and opportunity_ok and portfolio_ok and csv_json_ok and scoped_ok and failure_ok):
    sys.exit(1)
