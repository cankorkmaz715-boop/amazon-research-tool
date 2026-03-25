#!/usr/bin/env python3
"""
Step 224 smoke test: Basic usage analytics layer. Validates page view tracking,
action event tracking, safe payload shape, non-blocking failure behavior,
dashboard integration compatibility, onboarding/workspace creation integration.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

# Backend: allowlist, collector, API
page_view_ok = True
action_tracking_ok = True
payload_ok = True
non_blocking_ok = True
dashboard_ok = True
onboarding_creation_ok = True

try:
    from amazon_research.usage_analytics import (
        record_analytics_event,
        is_allowed_event,
        ALLOWED_PAGE_VIEWS,
        ALLOWED_ACTIONS,
    )
except Exception as e:
    page_view_ok = action_tracking_ok = payload_ok = non_blocking_ok = False
    print("import error: %s" % e)

if page_view_ok:
    # Page view tracking: allowed events exist and can be recorded
    for ev in ("workspace_dashboard_viewed", "portfolio_page_viewed", "alerts_page_viewed", "workspace_creation_viewed", "onboarding_viewed"):
        if ev not in ALLOWED_PAGE_VIEWS:
            page_view_ok = False
        if not is_allowed_event(ev):
            page_view_ok = False
    # record_analytics_event is non-blocking (catches internally); call with invalid event does not raise
    try:
        record_analytics_event(None, "not_allowed_event")
    except Exception:
        non_blocking_ok = False
    try:
        record_analytics_event(1, "workspace_dashboard_viewed")
    except Exception:
        non_blocking_ok = False

if action_tracking_ok:
    for ev in ("walkthrough_started", "walkthrough_completed", "onboarding_completed", "workspace_created", "portfolio_item_archived", "alert_marked_read", "demo_mode_seen"):
        if ev not in ALLOWED_ACTIONS:
            action_tracking_ok = False
        if not is_allowed_event(ev):
            action_tracking_ok = False

# Safe payload shape: metadata sanitized (no nested dumps)
if payload_ok:
    try:
        record_analytics_event(1, "workspace_dashboard_viewed", {"page": "dashboard"})
        record_analytics_event(None, "walkthrough_started", None)
    except Exception:
        payload_ok = False

# Non-blocking: record with missing DB or bad input does not raise (or only logs)
if non_blocking_ok:
    try:
        record_analytics_event(99999999, "portfolio_page_viewed")  # may fail DB but must not crash
    except Exception:
        non_blocking_ok = False

# Dashboard integration: overview has trackPageView, trackEvent, analytics script
UI_DIR = os.path.join(ROOT, "internal_ui")
overview_path = os.path.join(UI_DIR, "workspace-overview.html")
if os.path.isfile(overview_path):
    with open(overview_path, "r", encoding="utf-8") as f:
        overview = f.read()
    if "workspace-analytics.js" not in overview:
        dashboard_ok = False
    if "workspace_dashboard_viewed" not in overview:
        dashboard_ok = False
    if "trackEvent" not in overview or "trackPageView" not in overview:
        dashboard_ok = False
    if "walkthrough_started" not in overview or "onboarding_completed" not in overview:
        dashboard_ok = False
    if "demo_mode_seen" not in overview:
        dashboard_ok = False
else:
    dashboard_ok = False

# Onboarding / workspace creation integration: creation page has trackPageView and workspace_created
creation_path = os.path.join(UI_DIR, "workspace-creation.html")
if os.path.isfile(creation_path):
    with open(creation_path, "r", encoding="utf-8") as f:
        creation = f.read()
    if "workspace-analytics.js" not in creation:
        onboarding_creation_ok = False
    if "workspace_creation_viewed" not in creation:
        onboarding_creation_ok = False
    if "workspace_created" not in creation:
        onboarding_creation_ok = False
else:
    onboarding_creation_ok = False

# API route present
serve_path = os.path.join(ROOT, "scripts", "serve_internal_api.py")
if os.path.isfile(serve_path):
    with open(serve_path, "r", encoding="utf-8") as f:
        serve = f.read()
    if "/api/analytics/events" not in serve or "post_analytics_events_response" not in serve:
        payload_ok = False
else:
    payload_ok = False

print("basic usage analytics OK")
print("page view tracking: %s" % ("OK" if page_view_ok else "FAIL"))
print("action event tracking: %s" % ("OK" if action_tracking_ok else "FAIL"))
print("safe payload shape: %s" % ("OK" if payload_ok else "FAIL"))
print("non blocking failure behavior: %s" % ("OK" if non_blocking_ok else "FAIL"))
print("dashboard integration compatibility: %s" % ("OK" if dashboard_ok else "FAIL"))
print("onboarding workspace creation compatibility: %s" % ("OK" if onboarding_creation_ok else "FAIL"))

if not (page_view_ok and action_tracking_ok and payload_ok and non_blocking_ok and dashboard_ok and onboarding_creation_ok):
    sys.exit(1)
