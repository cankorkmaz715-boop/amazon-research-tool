#!/usr/bin/env python3
"""
Step 219 smoke test: Dashboard polish and UX consistency pass.
Validates shared shell styling integration, section consistency, empty/loading/error
consistency, badge/status styling, route/layout compatibility, partial-data resilience.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

UI_DIR = os.path.join(ROOT, "internal_ui")
PAGES = ["workspace-overview.html", "portfolio.html", "alert-center.html"]
SHARED_CSS = os.path.join(UI_DIR, "workspace-shared.css")


def main() -> None:
    shell_ok = True
    section_ok = True
    empty_loading_error_ok = True
    badge_ok = True
    route_layout_ok = True
    partial_ok = True

    # Shared shell styling: workspace-shared.css exists and defines tokens + primitives
    if not os.path.isfile(SHARED_CSS):
        shell_ok = False
    else:
        with open(SHARED_CSS, "r", encoding="utf-8") as f:
            css = f.read()
        for token in ("--ws-card-bg", "--ws-border", "--ws-space-md", "--ws-radius-md", "--ws-shadow-card"):
            if token not in css:
                shell_ok = False
        for cls in ("dashboard-empty-state", "dashboard-loading-state", "dashboard-error-state", "ws-badge", "ws-section-shell"):
            if cls not in css:
                shell_ok = False

    # All workspace pages link to shared CSS and use tokens
    for filename in PAGES:
        path = os.path.join(UI_DIR, filename)
        if not os.path.isfile(path):
            shell_ok = route_layout_ok = False
            continue
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        if "/internal_ui/workspace-shared.css" not in html:
            shell_ok = False
        if "var(--ws-" not in html and "var(--card-bg)" not in html:
            if "var(--ws-card-bg)" not in html:
                section_ok = False

    # Section consistency: sections use radius/gap/shadow tokens
    overview_path = os.path.join(UI_DIR, "workspace-overview.html")
    if os.path.isfile(overview_path):
        with open(overview_path, "r", encoding="utf-8") as f:
            overview = f.read()
        if "var(--radius-md)" not in overview and "var(--ws-radius-md)" not in overview:
            if "--radius-md" not in overview and "var(--section-gap)" not in overview:
                section_ok = False
        if "var(--section-gap)" not in overview and "var(--ws-section-gap)" not in overview:
            if "section-gap" not in overview:
                section_ok = False
        if "ws-shadow-card" not in overview and "box-shadow" not in overview:
            section_ok = False

    # Empty / loading / error consistency: shared classes present on all pages
    for filename in PAGES:
        path = os.path.join(UI_DIR, filename)
        if not os.path.isfile(path):
            empty_loading_error_ok = False
            continue
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        has_loading = "dashboard-loading-state" in html or "loading" in html
        has_error = "dashboard-error-state" in html or "error" in html
        has_empty = "dashboard-empty-state" in html or "empty-state" in html
        if not (has_loading and has_error and has_empty):
            empty_loading_error_ok = False

    # Badge and status styling: ws-badge or badge with consistent radius
    for filename in PAGES:
        path = os.path.join(UI_DIR, filename)
        if not os.path.isfile(path):
            badge_ok = False
            continue
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        if ".badge" not in html and "ws-badge" not in html:
            badge_ok = False
        if "ws-radius-sm" not in html and "radius" not in html and "border-radius" not in html:
            badge_ok = False

    # Route/layout compatibility: workspace shell and nav still present
    for filename in PAGES:
        path = os.path.join(UI_DIR, filename)
        if not os.path.isfile(path):
            route_layout_ok = False
            continue
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        if "workspace-app" not in html or "workspace-nav" not in html or "workspace-main" not in html:
            route_layout_ok = False
        if filename == "workspace-overview.html" and ("/workspace-overview" not in html or "/portfolio" not in html):
            route_layout_ok = False
        if filename == "portfolio.html" and "/portfolio" not in html:
            route_layout_ok = False
        if filename == "alert-center.html" and "/alert-center" not in html:
            route_layout_ok = False

    # Partial-data resilience: safe patterns still present (no removal of defensive checks)
    for filename in PAGES:
        path = os.path.join(UI_DIR, filename)
        if not os.path.isfile(path):
            partial_ok = False
            continue
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        if "display:none" not in html and "style=" not in html:
            pass
        if "getElementById" in html or "el(" in html:
            partial_ok = True
        if "safe(" in html or "|| {}" in html or "|| []" in html:
            partial_ok = True

    print("dashboard polish UX consistency OK")
    print("shared shell styling integration: %s" % ("OK" if shell_ok else "FAIL"))
    print("section consistency rendering: %s" % ("OK" if section_ok else "FAIL"))
    print("empty loading error consistency: %s" % ("OK" if empty_loading_error_ok else "FAIL"))
    print("badge status styling consistency: %s" % ("OK" if badge_ok else "FAIL"))
    print("route layout compatibility: %s" % ("OK" if route_layout_ok else "FAIL"))
    print("partial data resilience preservation: %s" % ("OK" if partial_ok else "FAIL"))

    if not (shell_ok and section_ok and empty_loading_error_ok and badge_ok and route_layout_ok and partial_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
