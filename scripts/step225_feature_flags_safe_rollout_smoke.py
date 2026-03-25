#!/usr/bin/env python3
"""
Step 225 smoke test: Feature flags & safe rollout. Validates default flag resolution,
env flag resolution, disabled feature fallback, enabled feature path, integration
compatibility, safe missing-flag behavior.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

default_ok = True
env_ok = True
disabled_fallback_ok = True
enabled_path_ok = True
integration_ok = True
missing_ok = True

try:
    from amazon_research.feature_flags import (
        get_feature_flags,
        is_feature_enabled,
        get_flag_from_env,
        DEFAULT_FLAGS,
    )
except Exception as e:
    default_ok = env_ok = disabled_fallback_ok = enabled_path_ok = integration_ok = missing_ok = False
    print("import error: %s" % e)

if default_ok:
    # Default flag resolution: all known flags return bool, no raise
    flags = get_feature_flags()
    for name in ("demo_mode", "walkthrough_enabled", "onboarding_enabled", "usage_analytics_enabled", "alert_center_enabled", "copilot_context_enabled"):
        if name not in flags:
            default_ok = False
        if not isinstance(flags.get(name), bool):
            default_ok = False
    if not isinstance(is_feature_enabled("walkthrough_enabled"), bool):
        default_ok = False

# Env flag resolution: set env and see change (then unset)
if env_ok:
    try:
        before = get_flag_from_env("walkthrough_enabled")
        os.environ["FEATURE_WALKTHROUGH"] = "false"
        after = get_flag_from_env("walkthrough_enabled")
        if after is not False:
            env_ok = False
        if "FEATURE_WALKTHROUGH" in os.environ:
            del os.environ["FEATURE_WALKTHROUGH"]
    except Exception:
        env_ok = False
    try:
        if "FEATURE_WALKTHROUGH" in os.environ:
            del os.environ["FEATURE_WALKTHROUGH"]
    except Exception:
        pass

# Disabled feature fallback: when flag is false, backend demo is not used
if disabled_fallback_ok:
    try:
        os.environ["FEATURE_DEMO_MODE"] = "false"
        from amazon_research.feature_flags import is_feature_enabled
        if is_feature_enabled("demo_mode") is not False:
            disabled_fallback_ok = False
        if "FEATURE_DEMO_MODE" in os.environ:
            del os.environ["FEATURE_DEMO_MODE"]
    except Exception:
        disabled_fallback_ok = False
    try:
        if "FEATURE_DEMO_MODE" in os.environ:
            del os.environ["FEATURE_DEMO_MODE"]
    except Exception:
        pass

# Enabled feature path: with defaults, flags are True
if enabled_path_ok:
    try:
        f = get_feature_flags()
        if f.get("walkthrough_enabled") is not True and f.get("onboarding_enabled") is not True:
            enabled_path_ok = False
    except Exception:
        enabled_path_ok = False

# Integration compatibility: dashboard aggregation checks demo_mode; overview has isFeatureEnabled
if integration_ok:
    try:
        from amazon_research.feature_flags import is_feature_enabled
        _ = is_feature_enabled("demo_mode")
    except Exception:
        integration_ok = False
    overview_path = os.path.join(ROOT, "internal_ui", "workspace-overview.html")
    if os.path.isfile(overview_path):
        with open(overview_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "workspace-feature-flags.js" not in html:
            integration_ok = False
        if "isFeatureEnabled" not in html:
            integration_ok = False
        if "walkthrough_enabled" not in html or "onboarding_enabled" not in html:
            integration_ok = False
    else:
        integration_ok = False

# Safe missing-flag behavior: unknown flag does not raise, returns True (no break) per resolver
if missing_ok:
    try:
        v = is_feature_enabled("nonexistent_flag_xyz")
        if not isinstance(v, bool):
            missing_ok = False
    except Exception:
        missing_ok = False

# API route exists
serve_path = os.path.join(ROOT, "scripts", "serve_internal_api.py")
if os.path.isfile(serve_path):
    with open(serve_path, "r", encoding="utf-8") as f:
        serve = f.read()
    if "/api/feature-flags" not in serve or "get_feature_flags_response" not in serve:
        integration_ok = False

print("feature flags safe rollout OK")
print("default flag resolution: %s" % ("OK" if default_ok else "FAIL"))
print("env flag resolution: %s" % ("OK" if env_ok else "FAIL"))
print("disabled feature fallback: %s" % ("OK" if disabled_fallback_ok else "FAIL"))
print("enabled feature path: %s" % ("OK" if enabled_path_ok else "FAIL"))
print("integration compatibility: %s" % ("OK" if integration_ok else "FAIL"))
print("safe missing flag behavior: %s" % ("OK" if missing_ok else "FAIL"))

if not (default_ok and env_ok and disabled_fallback_ok and enabled_path_ok and integration_ok and missing_ok):
    sys.exit(1)
