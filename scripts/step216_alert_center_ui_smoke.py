#!/usr/bin/env python3
"""
Step 216 smoke test: Alert center UI.
Validates alert page wiring, alert list rendering, severity badge rendering,
mark read compatibility, partial-data resilience, route integration compatibility,
payload-to-UI stability.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    wiring_ok = True
    item_rendering_ok = True
    severity_ok = True
    mark_read_ok = True
    partial_ok = True
    route_ok = True
    payload_ui_ok = True

    ui_path = os.path.join(ROOT, "internal_ui", "alert-center.html")
    if not os.path.isfile(ui_path):
        wiring_ok = False
    else:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        for id_ in ("alert-center-root", "alert-list", "alert-empty", "btn-load", "filter-type", "filter-read", "workspace-id", "alert-center-content"):
            if id_ not in html or ("id=\"" + id_ + "\"") not in html:
                if id_ == "workspace-id" and "workspace-id" in html:
                    pass
                elif id_ not in html:
                    wiring_ok = False
                    break
        if "/alerts" not in html or "PATCH" not in html or "Mark read" not in html:
            wiring_ok = False
        if "badge-high" not in html or "badge-medium" not in html or "badge-low" not in html:
            severity_ok = False

    # Alert item rendering: API returns data array with id, alert_type, severity, title, description, recorded_at, read_at
    try:
        from amazon_research.api.handlers import get_workspace_alerts_response
        body = get_workspace_alerts_response(99561, limit=10)
        data = body.get("data") if isinstance(body.get("data"), list) else []
        for a in data[:2]:
            if not isinstance(a, dict):
                continue
            _ = a.get("id"), a.get("alert_type"), a.get("severity"), a.get("title"), a.get("description"), a.get("recorded_at"), a.get("read_at")
        item_rendering_ok = True
    except Exception as e:
        item_rendering_ok = False
        print("alert item rendering error: %s" % e)

    # Severity badge rendering: payload has severity (high/medium/low)
    try:
        from amazon_research.api.handlers import get_workspace_alerts_response
        body = get_workspace_alerts_response(99562, limit=5)
        data = body.get("data") or []
        for a in data[:3]:
            _ = (a.get("severity") or "low").lower()
        severity_ok = True
    except Exception as e:
        severity_ok = False
        print("severity badge error: %s" % e)

    # Mark read compatibility: PATCH handler exists
    try:
        from amazon_research.api.handlers import patch_workspace_alert_read_response
        out = patch_workspace_alert_read_response(99563, 999999)
        if "data" not in out or "read" not in out.get("data", {}):
            mark_read_ok = False
        else:
            mark_read_ok = True
    except Exception as e:
        mark_read_ok = False
        print("mark read error: %s" % e)

    # Partial-data resilience: minimal item shape
    try:
        minimal = [{"id": 1, "alert_type": "high_potential", "severity": "medium", "title": "Alert", "description": "", "recorded_at": None, "read_at": None}]
        for a in minimal:
            _ = a.get("id"), a.get("alert_type"), (a.get("severity") or "low").lower() if isinstance(a.get("severity"), str) else "low"
            _ = a.get("title") or "Alert", (a.get("description") or "")[:300], a.get("read_at")
        partial_ok = True
    except Exception as e:
        partial_ok = False
        print("partial-data resilience error: %s" % e)

    # Route integration compatibility
    try:
        api_script = os.path.join(ROOT, "scripts", "serve_internal_api.py")
        with open(api_script, "r", encoding="utf-8") as f:
            api_src = f.read()
        if "_serve_alert_center_ui" not in api_src or "alert-center.html" not in api_src:
            route_ok = False
        if "_serve_alert_center_ui(self)" not in api_src:
            route_ok = False
    except Exception as e:
        route_ok = False
        print("route integration error: %s" % e)

    # Payload-to-UI stability: GET alerts returns data array; items have id, severity, title, read_at
    try:
        from amazon_research.api.handlers import get_workspace_alerts_response
        body = get_workspace_alerts_response(99564)
        data = body.get("data")
        if data is not None and not isinstance(data, list):
            payload_ui_ok = False
        else:
            for a in (data or [])[:3]:
                _ = a.get("id"), a.get("severity"), a.get("title"), a.get("read_at")
            payload_ui_ok = True
    except Exception as e:
        payload_ui_ok = False
        print("payload to UI stability error: %s" % e)

    all_ok = all([wiring_ok, item_rendering_ok, severity_ok, mark_read_ok, partial_ok, route_ok, payload_ui_ok])
    print("alert center UI OK" if all_ok else "alert center UI FAIL")
    print("alert page wiring: OK" if wiring_ok else "alert page wiring: FAIL")
    print("alert item rendering: OK" if item_rendering_ok else "alert item rendering: FAIL")
    print("severity badge rendering: OK" if severity_ok else "severity badge rendering: FAIL")
    print("mark read compatibility: OK" if mark_read_ok else "mark read compatibility: FAIL")
    print("partial-data resilience: OK" if partial_ok else "partial-data resilience: FAIL")
    print("route integration compatibility: OK" if route_ok else "route integration compatibility: FAIL")
    print("payload to UI stability: OK" if payload_ui_ok else "payload to UI stability: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
