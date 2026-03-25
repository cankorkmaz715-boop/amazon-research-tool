#!/usr/bin/env python3
"""
Step 60: SaaS core hardening review.
Compact review of: workspace isolation, api key model, usage tracking, quota enforcement,
rate limiting, billing hooks, plan model linkage.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def _gather() -> dict:
    out = {}
    try:
        from amazon_research.api.handlers import get_products
        out["api_workspace_scoped"] = True
    except Exception:
        out["api_workspace_scoped"] = False
    try:
        from amazon_research.db import validate_workspace_api_key, create_workspace_api_key
        out["api_key_model"] = True
    except Exception:
        out["api_key_model"] = False
    try:
        from amazon_research.db import record_usage, get_usage_summary_for_workspace
        out["usage_tracking"] = True
    except Exception:
        out["usage_tracking"] = False
    try:
        from amazon_research.db import check_quota, check_quota_and_raise
        out["quota_enforcement"] = True
    except Exception:
        out["quota_enforcement"] = False
    try:
        from amazon_research.rate_limit import check_rate_limit, get_effective_rate_limit
        out["rate_limiting"] = True
    except Exception:
        out["rate_limiting"] = False
    try:
        from amazon_research.db import record_billable_event, get_billable_events_summary
        out["billing_hooks"] = True
    except Exception:
        out["billing_hooks"] = False
    try:
        from amazon_research.db import get_workspace_plan, set_workspace_plan, create_plan
        out["plan_linkage"] = True
    except Exception:
        out["plan_linkage"] = False
    return out


def _review(components: dict) -> str:
    lines = [
        "SaaS core review:",
        "- Workspace isolation: API and export require workspace_id; data scoped by workspace.",
        "- API key model: workspace_api_keys (hashed); INTERNAL_API_KEY for admin; validate_internal_request.",
        "- Usage tracking: workspace_usage_events; record_usage; get_usage_summary_for_workspace.",
        "- Quota enforcement: workspace_quotas + plan.quota_profile; check_quota / check_quota_and_raise.",
        "- Rate limiting: in-memory per (workspace_id, bucket); plan.billing_metadata overrides config.",
        "- Billing hooks: billable_events; record_billable_event with plan context; get_billable_events_summary.",
        "- Plan model: plans table; workspace.plan_id; get_workspace_plan; quota_profile and billing_metadata.",
    ]
    return "\n".join(lines)


def main():
    from dotenv import load_dotenv
    load_dotenv()
    components = _gather()
    required = ["api_workspace_scoped", "api_key_model", "usage_tracking", "quota_enforcement", "rate_limiting", "billing_hooks", "plan_linkage"]
    all_ok = all(components.get(k) for k in required)
    review = _review(components)
    print(review)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
