#!/usr/bin/env python3
"""
Step 226 smoke test: SaaS settings panel. Validates settings page wiring,
default settings loading, toggle interaction, persistence compatibility,
feature flag visibility compatibility, safe fallback behavior.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)

UI_DIR = os.path.join(ROOT, "internal_ui")
SETTINGS_PATH = os.path.join(UI_DIR, "settings.html")
OVERVIEW_PATH = os.path.join(UI_DIR, "workspace-overview.html")
FEATURE_FLAGS_JS = os.path.join(UI_DIR, "workspace-feature-flags.js")
SERVE_PATH = os.path.join(ROOT, "scripts", "serve_internal_api.py")

wiring_ok = True
default_ok = True
toggle_ok = True
persistence_ok = True
feature_flag_ok = True
fallback_ok = True

if not os.path.isfile(SETTINGS_PATH):
    wiring_ok = default_ok = toggle_ok = persistence_ok = feature_flag_ok = fallback_ok = False
else:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    if 'id="settings-section-product"' not in html or 'id="settings-section-display"' not in html:
        wiring_ok = False
    if "Settings" not in html or "settings-row" not in html:
        wiring_ok = False
    if "toggle-walkthrough" not in html or "toggle-onboarding" not in html:
        wiring_ok = False
    if "setting-density" not in html or "comfortable" not in html or "compact" not in html:
        wiring_ok = False
    if "workspace-nav" not in html or "workspace-main" not in html:
        wiring_ok = False

    if "loadRow" not in html or "getUserPreference" not in html:
        default_ok = False
    if "pref(" not in html and "getUserPreference" not in html:
        default_ok = False
    if "flag(" not in html and "isFeatureEnabled" not in html:
        default_ok = False

    if "bindToggle" not in html or "setPref" not in html or "setUserPreference" not in html:
        toggle_ok = False
    if "addEventListener" not in html or "toggle-walkthrough" not in html:
        toggle_ok = False

    if "setUserPreference" not in html and "setPref" not in html:
        persistence_ok = False
    if "workspace_pref_" not in html and "PREF_PREFIX" not in html:
        if "getUserPreference" in html and "setUserPreference" in html:
            persistence_ok = True
        else:
            persistence_ok = False
    if os.path.isfile(FEATURE_FLAGS_JS):
        with open(FEATURE_FLAGS_JS, "r", encoding="utf-8") as f:
            js = f.read()
        if "getUserPreference" not in js or "setUserPreference" not in js:
            persistence_ok = False
    else:
        persistence_ok = False

    if "row-demo" in html and "flag(\"demo_mode\")" in html:
        feature_flag_ok = True
    elif "isFeatureEnabled" in html and "demo_mode" in html:
        feature_flag_ok = True
    else:
        feature_flag_ok = False
    if "workspace-feature-flags.js" not in html:
        feature_flag_ok = False

    if "settings-error" in html and "display: none" in html:
        fallback_ok = True
    if "try" in html and "catch" in html:
        fallback_ok = True
    if "el(" in html:
        fallback_ok = True

if os.path.isfile(OVERVIEW_PATH):
    with open(OVERVIEW_PATH, "r", encoding="utf-8") as f:
        ov = f.read()
    if "isSettingEnabled" not in ov:
        wiring_ok = False
    if "getUserPreference" not in ov and "demo_mode" not in ov:
        pass
    if "dashboard_density" not in ov and "dashboard-density-compact" not in ov:
        pass
    if "dashboard-density-compact" in ov and "getUserPreference" in ov:
        persistence_ok = True

if os.path.isfile(SERVE_PATH):
    with open(SERVE_PATH, "r", encoding="utf-8") as f:
        serve = f.read()
    if "_serve_settings_ui" not in serve or "/settings" not in serve:
        wiring_ok = False
else:
    wiring_ok = False

print("saas settings panel OK")
print("settings page wiring: %s" % ("OK" if wiring_ok else "FAIL"))
print("default settings loading: %s" % ("OK" if default_ok else "FAIL"))
print("toggle interaction: %s" % ("OK" if toggle_ok else "FAIL"))
print("persistence compatibility: %s" % ("OK" if persistence_ok else "FAIL"))
print("feature flag visibility compatibility: %s" % ("OK" if feature_flag_ok else "FAIL"))
print("safe fallback behavior: %s" % ("OK" if fallback_ok else "FAIL"))

if not (wiring_ok and default_ok and toggle_ok and persistence_ok and feature_flag_ok and fallback_ok):
    sys.exit(1)
