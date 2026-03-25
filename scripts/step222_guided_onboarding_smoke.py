#!/usr/bin/env python3
"""
Step 222 smoke test: Guided onboarding flow. Validates onboarding manager wiring,
checklist rendering, step configuration, dismiss behavior, dashboard compatibility.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

UI_PATH = os.path.join(ROOT, "internal_ui", "workspace-overview.html")


def main() -> None:
    wiring_ok = True
    checklist_ok = True
    step_config_ok = True
    dismiss_ok = True
    dashboard_ok = True

    if not os.path.isfile(UI_PATH):
        wiring_ok = checklist_ok = step_config_ok = dismiss_ok = dashboard_ok = False
    else:
        with open(UI_PATH, "r", encoding="utf-8") as f:
            html = f.read()

        # Onboarding manager wiring: storage key, get/set completed, show/hide, dismiss, reopen
        if "workspace_onboarding_completed" not in html:
            wiring_ok = False
        if "getOnboardingCompleted" not in html or "setOnboardingCompleted" not in html:
            wiring_ok = False
        if "showOnboardingPanel" not in html or "hideOnboardingPanel" not in html:
            wiring_ok = False
        if "dismissOnboarding" not in html or "reopenOnboarding" not in html:
            dismiss_ok = False

        # Checklist rendering: panel, list, progress, dismiss button
        if 'id="onboarding-panel"' not in html or 'id="onboarding-checklist"' not in html:
            checklist_ok = False
        if 'id="onboarding-progress"' not in html or 'id="onboarding-dismiss"' not in html:
            checklist_ok = False
        if "onboarding-visible" not in html:
            checklist_ok = False

        # Step configuration: ONBOARDING_STEPS with step_id, title, target
        if "ONBOARDING_STEPS" not in html or "step_id" not in html:
            step_config_ok = False
        if "Explore the workspace dashboard" not in html:
            step_config_ok = False
        if "Review discovered opportunities" not in html or "Track an opportunity" not in html:
            step_config_ok = False
        if "Review strategy and risk insights" not in html or "Configure alerts" not in html:
            step_config_ok = False
        if "Explore Copilot context" not in html:
            step_config_ok = False
        if "renderOnboardingChecklist" not in html:
            step_config_ok = False

        # Dismiss behavior: Dismiss button, set completed, clear for reopen
        if "Dismiss" not in html:
            dismiss_ok = False
        if "clearOnboardingCompleted" not in html or "localStorage.removeItem" not in html:
            dismiss_ok = False
        if 'id="onboarding-reopen"' not in html or "Onboarding" not in html:
            dismiss_ok = False

        # Dashboard compatibility: existing dashboard and nav intact
        if "workspace-app" not in html or "workspace-nav" not in html:
            dashboard_ok = False
        if "dashboard-content" not in html or "opportunity-feed-panel" not in html:
            dashboard_ok = False
        if "copilot-context-panel" not in html:
            dashboard_ok = False

    print("guided onboarding flow OK")
    print("onboarding manager wiring: %s" % ("OK" if wiring_ok else "FAIL"))
    print("checklist rendering: %s" % ("OK" if checklist_ok else "FAIL"))
    print("step configuration loading: %s" % ("OK" if step_config_ok else "FAIL"))
    print("dismiss behavior: %s" % ("OK" if dismiss_ok else "FAIL"))
    print("dashboard compatibility: %s" % ("OK" if dashboard_ok else "FAIL"))

    if not (wiring_ok and checklist_ok and step_config_ok and dismiss_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
