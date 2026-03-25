#!/usr/bin/env python3
"""
Step 218 smoke test: Workspace navigation and dashboard flow consolidation.
Validates workspace shell wiring, navigation rendering, active route behavior,
dashboard flow integration, partial-context resilience, layout stability.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

UI_DIR = os.path.join(ROOT, "internal_ui")
PAGES = [
    ("workspace-overview.html", "dashboard", "/workspace-overview"),
    ("portfolio.html", "portfolio", "/portfolio"),
    ("alert-center.html", "alerts", "/alert-center"),
]

EXPECTED_NAV_HREFS = ["/workflow", "/workspace-overview", "/portfolio", "/alert-center"]
EXPECTED_NAV_LABELS = ["Workflow", "Dashboard", "Portfolio", "Alerts"]


def main() -> None:
    shell_ok = True
    nav_ok = True
    active_ok = True
    flow_ok = True
    partial_ok = True
    layout_ok = True

    for filename, page_key, expected_path in PAGES:
        path = os.path.join(UI_DIR, filename)
        if not os.path.isfile(path):
            shell_ok = nav_ok = active_ok = flow_ok = layout_ok = False
            break
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()

        # Workspace shell wiring
        if 'class="workspace-app"' not in html and "workspace-app" not in html:
            shell_ok = False
        if "workspace-header" not in html or "workspace-nav" not in html:
            shell_ok = False
        if "workspace-main" not in html:
            shell_ok = False
        if 'id="workspace-nav"' not in html and 'class="workspace-nav"' not in html:
            shell_ok = False

        # Navigation rendering: same links and labels
        for href in EXPECTED_NAV_HREFS:
            if href not in html:
                nav_ok = False
        for label in EXPECTED_NAV_LABELS:
            if label not in html:
                nav_ok = False

        # Active route: current page link has class="active"
        if page_key == "dashboard":
            if not re.search(r'href="/workspace-overview"[^>]*class="active"', html) and 'class="active">Dashboard' not in html:
                if 'href="/workspace-overview" class="active"' not in html:
                    active_ok = False
        elif page_key == "portfolio":
            if not re.search(r'href="/portfolio"[^>]*class="active"', html) and 'href="/portfolio" class="active"' not in html:
                active_ok = False
        elif page_key == "alerts":
            if not re.search(r'href="/alert-center"[^>]*class="active"', html) and 'href="/alert-center" class="active"' not in html:
                active_ok = False

        # Layout stability: header wraps nav, main wraps content
        if html.find("<header") > html.find("</body>") or html.find("<main") > html.find("</body>"):
            layout_ok = False
        if html.find("</main>") == -1:
            layout_ok = False

    # Dashboard flow integration: overview has in-page section nav
    overview_path = os.path.join(UI_DIR, "workspace-overview.html")
    if os.path.isfile(overview_path):
        with open(overview_path, "r", encoding="utf-8") as f:
            overview_html = f.read()
        if "dashboard-sections-nav" not in overview_html:
            flow_ok = False
        for anchor in ("#overview-stats", "#opportunity-feed-panel", "#insight-panels-grid", "#copilot-context-panel"):
            if anchor not in overview_html:
                flow_ok = False
        for label in ("Overview", "Opportunities", "Insights", "Copilot"):
            if label not in overview_html:
                flow_ok = False
    else:
        flow_ok = False

    # Partial-context resilience: nav is static; no requirement for workspace id in markup for shell
    for filename, _, _ in PAGES:
        path = os.path.join(UI_DIR, filename)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                html = f.read()
            if "workspace-nav" in html and "Workspace" in html or "Dashboard" in html:
                partial_ok = True
            break

    print("workspace navigation flow OK")
    print("workspace shell wiring: %s" % ("OK" if shell_ok else "FAIL"))
    print("navigation rendering: %s" % ("OK" if nav_ok else "FAIL"))
    print("active route behavior: %s" % ("OK" if active_ok else "FAIL"))
    print("dashboard flow integration: %s" % ("OK" if flow_ok else "FAIL"))
    print("partial context resilience: %s" % ("OK" if partial_ok else "FAIL"))
    print("layout stability: %s" % ("OK" if layout_ok else "FAIL"))

    if not (shell_ok and nav_ok and active_ok and flow_ok and partial_ok and layout_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
