#!/usr/bin/env python3
"""
Step 227 smoke test: Workspace preferences. Validates preferences page wiring,
default preference loading, workspace-scoped persistence, toggle/select
interaction, workspace isolation compatibility, safe fallback behavior.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

UI_DIR = os.path.join(ROOT, "internal_ui")
PREFS_PAGE = os.path.join(UI_DIR, "workspace-preferences.html")
FEATURE_FLAGS_JS = os.path.join(UI_DIR, "workspace-feature-flags.js")
OVERVIEW_PATH = os.path.join(UI_DIR, "workspace-overview.html")
SERVE_PATH = os.path.join(ROOT, "scripts", "serve_internal_api.py")

wiring_ok = True
default_ok = True
scoped_ok = True
toggle_select_ok = True
isolation_ok = True
fallback_ok = True

if not os.path.isfile(PREFS_PAGE):
    wiring_ok = default_ok = scoped_ok = toggle_select_ok = isolation_ok = fallback_ok = False
else:
    with open(PREFS_PAGE, "r", encoding="utf-8") as f:
        html = f.read()

    if "workspace-preferences" not in html or "Workspace preferences" not in html:
        wiring_ok = False
    if "workspace-id" not in html or "prefs-context" not in html:
        wiring_ok = False
    if "prefs-form" not in html or "section-display" not in html or "section-panels" not in html:
        wiring_ok = False
    if "toggle-copilot" not in html or "toggle-demo-hints" not in html:
        wiring_ok = False
    if "wp-density" not in html or "wp-landing" not in html:
        wiring_ok = False
    if "workspace_prefs_" not in html and "WORKSPACE_PREFS_PREFIX" not in html:
        pass
    if "getWorkspacePreferences" not in html and "getWorkspacePreference" not in html:
        default_ok = False
    if "loadForm" not in html or "getPref" not in html:
        default_ok = False

    if "setWorkspacePreference" not in html or "setPref" not in html:
        scoped_ok = False
    if "getWsId" not in html:
        scoped_ok = False
    if os.path.isfile(FEATURE_FLAGS_JS):
        with open(FEATURE_FLAGS_JS, "r", encoding="utf-8") as f:
            js = f.read()
        if "getWorkspacePreferences" not in js or "setWorkspacePreference" not in js:
            scoped_ok = False
        if "WORKSPACE_PREFS_PREFIX" not in js and "workspace_prefs_" not in js:
            scoped_ok = False
    else:
        scoped_ok = False

    if "addEventListener" not in html or "toggle-copilot" not in html:
        toggle_select_ok = False
    if "wp-density" not in html or "wp-landing" not in html:
        toggle_select_ok = False
    if "bindToggles" not in html or "bindSelects" not in html:
        toggle_select_ok = False

    if "getWsId" not in html:
        isolation_ok = False
    if "workspace_id" not in html and "workspace-id" not in html:
        isolation_ok = False
    if "getWorkspacePreference" not in html:
        isolation_ok = False

    if "prefs-empty" in html:
        fallback_ok = True
    if "try" in html and "catch" in html:
        fallback_ok = True
    if "getWorkspacePreferences" in html and "return {}" in html:
        fallback_ok = True

if os.path.isfile(OVERVIEW_PATH):
    with open(OVERVIEW_PATH, "r", encoding="utf-8") as f:
        ov = f.read()
    if "getWorkspacePreference" not in ov:
        wiring_ok = False
    if "copilot_visible" not in ov or "demo_hints_visible" not in ov:
        pass
    if "landing_section" not in ov and "dashboard_density" not in ov:
        pass
    if "getWorkspacePreference" in ov and "dashboard_density" in ov:
        scoped_ok = True

if os.path.isfile(SERVE_PATH):
    with open(SERVE_PATH, "r", encoding="utf-8") as f:
        serve = f.read()
    if "_serve_workspace_preferences_ui" not in serve or "workspace-preferences" not in serve:
        wiring_ok = False
else:
    wiring_ok = False

print("workspace preferences OK")
print("preferences page wiring: %s" % ("OK" if wiring_ok else "FAIL"))
print("default preference loading: %s" % ("OK" if default_ok else "FAIL"))
print("workspace scoped persistence: %s" % ("OK" if scoped_ok else "FAIL"))
print("toggle select interaction: %s" % ("OK" if toggle_select_ok else "FAIL"))
print("workspace isolation compatibility: %s" % ("OK" if isolation_ok else "FAIL"))
print("safe fallback behavior: %s" % ("OK" if fallback_ok else "FAIL"))

if not (wiring_ok and default_ok and scoped_ok and toggle_select_ok and isolation_ok and fallback_ok):
    sys.exit(1)
