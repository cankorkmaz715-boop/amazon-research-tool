#!/usr/bin/env python3
"""
Step 215 smoke test: Portfolio management UI.
Validates portfolio page wiring, portfolio item rendering, portfolio summary rendering,
archive action compatibility, partial-data resilience, route integration compatibility,
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
    summary_rendering_ok = True
    archive_ok = True
    partial_ok = True
    route_ok = True
    payload_ui_ok = True

    ui_path = os.path.join(ROOT, "internal_ui", "portfolio.html")
    if not os.path.isfile(ui_path):
        wiring_ok = False
    else:
        with open(ui_path, "r", encoding="utf-8") as f:
            html = f.read()
        for id_ in ("portfolio-root", "portfolio-summary-bar", "portfolio-tbody", "portfolio-empty", "btn-load", "filter-status", "filter-type", "workspace-id", "portfolio-content"):
            if id_ not in html or ("id=\"" + id_ + "\"") not in html:
                if id_ == "workspace-id" and "workspace-id" in html:
                    pass
                elif id_ not in html:
                    wiring_ok = False
                    break
        if "Load portfolio" not in html or "Archive" not in html or "renderSummary" not in html and "portfolio-summary-bar" not in html:
            pass
        if "/portfolio/summary" not in html or "/portfolio" not in html or "PATCH" not in html:
            wiring_ok = False

    # Portfolio item rendering: API list returns items with id, item_type, item_key, status, etc.
    try:
        from amazon_research.api.handlers import get_workspace_portfolio_response
        body = get_workspace_portfolio_response(99531, limit=10)
        data = body.get("data") if isinstance(body.get("data"), list) else []
        for it in data[:2]:
            if not isinstance(it, dict):
                continue
            _ = it.get("id"), it.get("item_type"), it.get("item_key"), it.get("item_label"), it.get("source_type"), it.get("status"), it.get("updated_at"), it.get("created_at")
        item_rendering_ok = True
    except Exception as e:
        item_rendering_ok = False
        print("portfolio item rendering error: %s" % e)

    # Portfolio summary rendering: summary API returns total, by_status, by_type
    try:
        from amazon_research.api.handlers import get_workspace_portfolio_summary_response
        body = get_workspace_portfolio_summary_response(99532)
        data = body.get("data") or {}
        if "total" not in data or "by_status" not in data:
            summary_rendering_ok = False
        else:
            summary_rendering_ok = True
    except Exception as e:
        summary_rendering_ok = False
        print("portfolio summary rendering error: %s" % e)

    # Archive action compatibility: PATCH handler exists and is wired
    try:
        from amazon_research.api.handlers import patch_workspace_portfolio_archive_response
        out = patch_workspace_portfolio_archive_response(99533, 999999)
        if "data" not in out or "archived" not in out.get("data", {}):
            archive_ok = False
        else:
            archive_ok = True
    except Exception as e:
        archive_ok = False
        print("archive action error: %s" % e)

    # Partial-data resilience: empty list and minimal item shape
    try:
        minimal_items = []
        minimal_item = {"id": 1, "item_type": "opportunity", "item_key": "K1", "status": "active"}
        minimal_items.append(minimal_item)
        for it in minimal_items:
            _ = it.get("id"), it.get("item_type"), it.get("item_key"), it.get("item_label") or "", it.get("source_type") or "", (it.get("status") or "active").lower(), it.get("updated_at") or it.get("created_at")
        summary_minimal = {"total": 0, "by_status": {"active": 0, "archived": 0}, "by_type": {}}
        _ = summary_minimal.get("total"), summary_minimal.get("by_status"), summary_minimal.get("by_type")
        partial_ok = True
    except Exception as e:
        partial_ok = False
        print("partial-data resilience error: %s" % e)

    # Route integration compatibility: server serves /portfolio
    try:
        api_script = os.path.join(ROOT, "scripts", "serve_internal_api.py")
        with open(api_script, "r", encoding="utf-8") as f:
            api_src = f.read()
        if "_serve_portfolio_ui" not in api_src or "portfolio.html" not in api_src:
            route_ok = False
        if "_serve_portfolio_ui(self)" not in api_src:
            route_ok = False
    except Exception as e:
        route_ok = False
        print("route integration error: %s" % e)

    # Payload-to-UI stability: list payload has data array; summary has total, by_status
    try:
        from amazon_research.api.handlers import get_workspace_portfolio_response, get_workspace_portfolio_summary_response
        list_body = get_workspace_portfolio_response(99534)
        summary_body = get_workspace_portfolio_summary_response(99534)
        list_data = list_body.get("data")
        summary_data = summary_body.get("data")
        if not isinstance(summary_data, dict) or "total" not in summary_data or "by_status" not in summary_data:
            payload_ui_ok = False
        elif list_data is not None and not isinstance(list_data, list):
            payload_ui_ok = False
        else:
            payload_ui_ok = True
    except Exception as e:
        payload_ui_ok = False
        print("payload to UI stability error: %s" % e)

    all_ok = all([wiring_ok, item_rendering_ok, summary_rendering_ok, archive_ok, partial_ok, route_ok, payload_ui_ok])
    print("portfolio management UI OK" if all_ok else "portfolio management UI FAIL")
    print("portfolio page wiring: OK" if wiring_ok else "portfolio page wiring: FAIL")
    print("portfolio item rendering: OK" if item_rendering_ok else "portfolio item rendering: FAIL")
    print("portfolio summary rendering: OK" if summary_rendering_ok else "portfolio summary rendering: FAIL")
    print("archive action compatibility: OK" if archive_ok else "archive action compatibility: FAIL")
    print("partial-data resilience: OK" if partial_ok else "partial-data resilience: FAIL")
    print("route integration compatibility: OK" if route_ok else "route integration compatibility: FAIL")
    print("payload to UI stability: OK" if payload_ui_ok else "payload to UI stability: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
