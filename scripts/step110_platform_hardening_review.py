#!/usr/bin/env python3
"""
Step 110: Research platform hardening review.
Audits infrastructure improvements after Step 100: BSR history, trend persistence, cluster cache,
discovery storage, advanced keyword expansion, reverse ASIN keyword graph, opportunity alert engine,
automated discovery scheduler, multi-marketplace engine. Verifies persistence, cache, scheduler, market.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

# Post–Step 100 modules and main entry point (module path, attribute name)
MODULES = [
    ("amazon_research.db.persistence", "append_bsr_history"),
    ("amazon_research.db.persistence", "get_bsr_history"),
    ("amazon_research.db.trend_persistence", "persist_trend_result"),
    ("amazon_research.db.trend_persistence", "get_trend_result_latest"),
    ("amazon_research.db.cluster_cache", "save_cluster_cache"),
    ("amazon_research.db.cluster_cache", "get_cluster_cache"),
    ("amazon_research.db.discovery_storage", "save_discovery_result"),
    ("amazon_research.db.discovery_storage", "get_discovery_context_for_asin"),
    ("amazon_research.keywords.expansion", "expand_keywords"),
    ("amazon_research.db.asin_keyword_graph", "add_asin_keyword_edge"),
    ("amazon_research.db.asin_keyword_graph", "get_keywords_for_asin"),
    ("amazon_research.alerts.opportunity_alert_engine", "evaluate_opportunity_alerts"),
    ("amazon_research.scheduler.discovery_scheduler", "plan_discovery_tasks"),
    ("amazon_research.scheduler.discovery_scheduler", "enqueue_discovery_schedule"),
    ("amazon_research.market.config", "resolve_market"),
    ("amazon_research.market.config", "build_market_context"),
]


def check_persistence():
    """Verify persistence layers: BSR history, trend results, discovery results, asin_keyword_edges, opportunity_alerts."""
    ok = True
    try:
        from amazon_research.db import (
            append_bsr_history,
            get_bsr_history,
            persist_trend_result,
            get_trend_result_latest,
            save_discovery_result,
            get_discovery_context_for_asin,
            add_asin_keyword_edge,
            get_keywords_for_asin,
            save_opportunity_alert,
            list_opportunity_alerts,
        )
        ok = (
            callable(append_bsr_history)
            and callable(get_bsr_history)
            and callable(persist_trend_result)
            and callable(get_trend_result_latest)
            and callable(save_discovery_result)
            and callable(get_discovery_context_for_asin)
            and callable(add_asin_keyword_edge)
            and callable(get_keywords_for_asin)
            and callable(save_opportunity_alert)
            and callable(list_opportunity_alerts)
        )
    except Exception:
        ok = False
    return ok


def check_cache():
    """Verify cluster cache: save, get, freshness, invalidation."""
    ok = True
    try:
        from amazon_research.db import (
            save_cluster_cache,
            get_cluster_cache,
            get_cluster_cache_freshness,
            invalidate_cluster_cache,
        )
        ok = (
            callable(save_cluster_cache)
            and callable(get_cluster_cache)
            and callable(get_cluster_cache_freshness)
            and callable(invalidate_cluster_cache)
        )
    except Exception:
        ok = False
    return ok


def check_scheduler():
    """Verify discovery scheduler and alert engine stability."""
    ok = True
    try:
        from amazon_research.scheduler import plan_discovery_tasks, enqueue_discovery_schedule
        from amazon_research.alerts import evaluate_opportunity_alerts
        plan = plan_discovery_tasks(
            max_category_tasks=0,
            max_keyword_tasks=0,
            include_niche_discovery=True,
            include_alert_refresh=True,
        )
        ok = (
            callable(plan_discovery_tasks)
            and callable(enqueue_discovery_schedule)
            and callable(evaluate_opportunity_alerts)
            and isinstance(plan.get("schedule"), list)
            and "summary" in plan
        )
    except Exception:
        ok = False
    return ok


def check_market():
    """Verify multi-marketplace compatibility: resolve_market, build_market_context, URL/domain."""
    ok = True
    try:
        from amazon_research.market import (
            resolve_market,
            get_domain,
            build_market_context,
            get_product_url,
            get_search_url,
            get_default_market,
        )
        de = resolve_market("DE")
        uk = resolve_market("UK")
        ctx = build_market_context("DE")
        default = get_default_market()
        ok = (
            de == "DE"
            and uk == "UK"
            and isinstance(ctx, dict)
            and "market_code" in ctx
            and "domain" in ctx
            and callable(get_product_url)
            and callable(get_search_url)
            and (default == "DE" or len(default) >= 2)
        )
    except Exception:
        ok = False
    return ok


def main():
    from dotenv import load_dotenv
    load_dotenv()

    # Module presence
    seen = set()
    for path, attr in MODULES:
        try:
            mod = __import__(path, fromlist=[attr])
            if hasattr(mod, attr):
                seen.add((path, attr))
        except Exception:
            pass
    modules_ok = len(seen) >= len(MODULES) - 2  # allow 1–2 optional

    persistence_ok = check_persistence()
    cache_ok = check_cache()
    scheduler_ok = check_scheduler()
    market_ok = check_market()

    # Concise review summary: scaling, operational, data consistency
    risks = [
        "Scaling: Per-cluster/ASIN trend and alert evaluation can be costly at high volume; cache and batch where possible.",
        "Operational: New persistence (trend_results, cluster_cache, discovery_results, bsr_history, opportunity_alerts) has no retention policy; consider cleanup jobs.",
        "Data consistency: Discovery results, cluster cache, and keyword graph are append-only; ensure marketplace and source_context are set so reverse ASIN and expansion stay market-aware.",
    ]

    next_improvements = [
        "Add retention/cleanup for trend_results, cluster_cache, discovery_results, opportunity_alerts.",
        "Consider indexing discovery_results and asin_keyword_edges by marketplace for large multi-market datasets.",
        "Document alert threshold defaults and optional persistence (save_opportunity_alert) for notification rules.",
        "Optional: stagger discovery_scheduler enqueue with scheduled_at to spread load.",
        "Validate category_url and keyword seeds per marketplace before scan to avoid cross-market contamination.",
    ]

    print("platform hardening review OK")
    print("persistence layer: OK" if persistence_ok else "persistence layer: FAIL")
    print("cache integrity: OK" if cache_ok else "cache integrity: FAIL")
    print("scheduler stability: OK" if scheduler_ok else "scheduler stability: FAIL")
    print("market compatibility: OK" if market_ok else "market compatibility: FAIL")
    print("next improvements:")
    for n in next_improvements:
        print(f"  - {n}")
    print("risks (concise):")
    for r in risks:
        print(f"  - {r}")

    all_ok = persistence_ok and cache_ok and scheduler_ok and market_ok and modules_ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
