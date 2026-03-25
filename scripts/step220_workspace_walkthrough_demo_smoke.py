#!/usr/bin/env python3
"""
Step 220 smoke test: Workspace walkthrough and demo layer.
Validates walkthrough manager wiring, step loading, overlay rendering,
skip/complete behavior, empty workspace hint behavior, dashboard compatibility.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

UI_PATH = os.path.join(ROOT, "internal_ui", "workspace-overview.html")


def main() -> None:
    wiring_ok = True
    step_loading_ok = True
    overlay_ok = True
    skip_complete_ok = True
    empty_hint_ok = True
    dashboard_ok = True

    if not os.path.isfile(UI_PATH):
        wiring_ok = step_loading_ok = overlay_ok = skip_complete_ok = empty_hint_ok = dashboard_ok = False
    else:
        with open(UI_PATH, "r", encoding="utf-8") as f:
            html = f.read()

        # Walkthrough manager wiring: storage key, steps config, start/hide/next/prev/skip/complete
        if "workspace_walkthrough_completed" not in html:
            wiring_ok = False
        if "getWalkthroughCompleted" not in html or "setWalkthroughCompleted" not in html:
            wiring_ok = False
        if "walkthroughStart" not in html or "walkthroughHide" not in html:
            wiring_ok = False
        if "walkthroughSkip" not in html or "walkthroughComplete" not in html:
            skip_complete_ok = False
        if "walkthroughNext" not in html or "walkthroughPrev" not in html:
            wiring_ok = False

        # Walkthrough step loading: steps with step_id, title, description, target_element
        if "WALKTHROUGH_STEPS" not in html or "step_id" not in html:
            step_loading_ok = False
        if "Welcome to your workspace dashboard" not in html:
            step_loading_ok = False
        if "opportunity feed" not in html.lower() or "Strategy, risk" not in html or "Copilot context" not in html:
            step_loading_ok = False
        if "target_element" not in html:
            step_loading_ok = False

        # Overlay rendering: overlay container, step card, title, desc, nav buttons
        if 'id="walkthrough-overlay"' not in html:
            overlay_ok = False
        if 'id="walkthrough-step-card"' not in html:
            overlay_ok = False
        if 'id="walkthrough-step-title"' not in html or 'id="walkthrough-step-desc"' not in html:
            overlay_ok = False
        if 'id="walkthrough-skip"' not in html or 'id="walkthrough-prev"' not in html or 'id="walkthrough-next"' not in html:
            overlay_ok = False
        if "walkthrough-visible" not in html:
            overlay_ok = False

        # Skip/complete behavior: Skip tour button, localStorage set on complete
        if "Skip tour" not in html:
            skip_complete_ok = False
        if "localStorage.setItem" not in html and "setWalkthroughCompleted" not in html:
            skip_complete_ok = False

        # Empty workspace hint behavior: hints when data empty, no fake data
        if "walkthrough-empty-hint" not in html:
            empty_hint_ok = False
        if "Your opportunity feed will show discovered" not in html:
            empty_hint_ok = False
        if "Risk insights appear when signals" not in html:
            empty_hint_ok = False
        if "Copilot context shows what the system sees" not in html:
            empty_hint_ok = False

        # Dashboard compatibility: workspace shell and dashboard content intact
        if "workspace-app" not in html or "workspace-nav" not in html:
            dashboard_ok = False
        if "dashboard-content" not in html or "opportunity-feed-panel" not in html:
            dashboard_ok = False
        if "insight-panels-grid" not in html or "copilot-context-panel" not in html:
            dashboard_ok = False
        if "walkthrough-trigger" not in html and "Take a tour" not in html:
            dashboard_ok = False

    print("workspace walkthrough demo layer OK")
    print("walkthrough manager wiring: %s" % ("OK" if wiring_ok else "FAIL"))
    print("walkthrough step loading: %s" % ("OK" if step_loading_ok else "FAIL"))
    print("overlay rendering: %s" % ("OK" if overlay_ok else "FAIL"))
    print("skip complete behavior: %s" % ("OK" if skip_complete_ok else "FAIL"))
    print("empty workspace hint behavior: %s" % ("OK" if empty_hint_ok else "FAIL"))
    print("dashboard compatibility: %s" % ("OK" if dashboard_ok else "FAIL"))

    if not (wiring_ok and step_loading_ok and overlay_ok and skip_complete_ok and empty_hint_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
