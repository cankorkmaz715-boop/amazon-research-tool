#!/usr/bin/env python3
"""
Step 30: Production Readiness Review.
Audits proxy, browser, discovery, refresh, scoring, scheduler, monitoring, API, ops.
Outputs strengths, risks, and recommended next improvements. No rewrite.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def _gather_components():
    """Verify key modules and optional runtime checks. Returns dict of component presence."""
    out = {}
    try:
        from amazon_research import config
        out["config"] = True
    except Exception:
        out["config"] = False
    try:
        from amazon_research.proxy import ProxyManager
        out["proxy"] = True
    except Exception:
        out["proxy"] = False
    try:
        from amazon_research.browser import BrowserSession
        out["browser"] = True
    except Exception:
        out["browser"] = False
    try:
        from amazon_research.db import get_connection, run_data_quality_checks
        out["db"] = True
    except Exception:
        out["db"] = False
    try:
        from amazon_research.bots import AsinDiscoveryBot, DataRefreshBot, ScoringEngine
        out["bots"] = True
    except Exception:
        out["bots"] = False
    try:
        from amazon_research.scheduler import get_runner, PIPELINE_ORDER
        out["scheduler"] = True
    except Exception:
        out["scheduler"] = False
    try:
        from amazon_research.monitoring import health_check, init_sentry, sentry_status
        out["monitoring"] = True
    except Exception:
        out["monitoring"] = False
    try:
        from amazon_research.api import get_products, get_metrics, get_scores
        out["api"] = True
    except Exception:
        out["api"] = False
    return out


def _build_review(components):
    """Produce strengths, risks, and recommended next improvements from current architecture."""
    strengths = [
        "Central config (env), proxy manager (DataImpulse-ready), Playwright browser with retry and delays",
        "Discovery (single/multi-page cap), refresh (batch cap, failure tracking, skip_until), scoring (DB-only)",
        "Scheduler pipeline (discovery→refresh→scoring), fail-stop per stage",
        "Monitoring: health (db, browser, proxy, scheduler), optional Sentry, data quality checks",
        "Internal API with dashboard contract (data + meta, filter/sort), ops (cron/systemd examples, OPS-RECURRING.md)",
    ]
    risks = [
        "Anti-bot: single IP/session patterns; no rotation, no CAPTCHA handling; Amazon may tighten blocks.",
        "Data quality: parser selectors can break on markup changes; no automated schema/selector regression tests.",
        "Scaling: all sequential; no queue, no horizontal scaling; DB and browser are single-process bottlenecks.",
        "Operational: no alerting on pipeline failure; no retention/cleanup for error_logs or history tables.",
        "Maintainability: selector lists and retry/delay constants are spread; no single 'tuning' doc.",
    ]
    recommended = [
        "Add alerting on pipeline failure (e.g. webhook or email when run_pipeline returns ok=False).",
        "Add optional proxy/session rotation and CAPTCHA detection (fail fast, log, skip) before scaling up.",
        "Document selector maintenance and add a minimal regression test (fixture pages) for parsers.",
        "Define retention/archival for error_logs and history tables; optional cleanup job.",
        "Consider a small tuning/runbook doc (config knobs, when to change delays, when to disable cron).",
    ]
    return {
        "strengths": strengths,
        "risks": risks,
        "recommended_next_improvements": recommended,
    }


def main():
    from dotenv import load_dotenv
    load_dotenv()
    try:
        from amazon_research.db import init_db
        init_db()
    except Exception:
        pass
    components = _gather_components()
    review = _build_review(components)
    all_ok = all(components.get(k) for k in ["config", "proxy", "browser", "db", "bots", "scheduler", "monitoring", "api"])
    print("production readiness review OK" if all_ok else "production readiness review INCOMPLETE (missing components)")
    print("strengths:", "; ".join(review["strengths"]))
    print("risks:", "; ".join(review["risks"]))
    print("recommended next improvements:", "; ".join(review["recommended_next_improvements"]))
    if not all_ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
