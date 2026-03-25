#!/usr/bin/env python3
"""Step 184: Multi-market crawler activation – market separation, domain routing, seed activation, scheduler compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    market_separation_ok = False
    domain_routing_ok = False
    seed_activation_ok = False
    scheduler_compat_ok = False

    # 1) Market separation: production markets DE, US, AU; activation items have single market each
    try:
        from amazon_research.scheduler.multi_market_activation import (
            get_production_markets,
            get_multi_market_activation,
            TARGET_TYPE_CATEGORY,
            TARGET_TYPE_KEYWORD,
        )
        markets = get_production_markets()
        market_separation_ok = isinstance(markets, list) and "DE" in markets and "US" in markets and "AU" in markets
        targets = get_multi_market_activation(markets=["DE", "US"], workspace_id=None, limit_per_type=2)
        for t in targets:
            if t.get("market") not in ("DE", "US", "AU"):
                market_separation_ok = False
                break
            if not all(k in t for k in ("market", "target_type", "target_id", "activation_status", "timestamp")):
                market_separation_ok = False
                break
        else:
            market_separation_ok = market_separation_ok and True
    except Exception as e:
        print(f"market separation FAIL: {e}")
        market_separation_ok = False

    # 2) Domain routing: build_category_url_for_market and get_search_url_for_market return market-specific URLs
    try:
        from amazon_research.scheduler.multi_market_activation import (
            build_category_url_for_market,
            get_search_url_for_market,
        )
        from amazon_research.market import get_domain, PRODUCTION_MARKETS
        domain_routing_ok = True
        for m in ["DE", "US", "AU"]:
            d = get_domain(m)
            if m == "DE" and "amazon.de" not in d:
                domain_routing_ok = False
            if m == "US" and "amazon.com" not in d:
                domain_routing_ok = False
            if m == "AU" and "amazon.com.au" not in d:
                domain_routing_ok = False
            cat_url = build_category_url_for_market("/gp/bestsellers", m)
            if d.replace("www.", "") not in cat_url:
                domain_routing_ok = False
            search_url = get_search_url_for_market("test", m)
            if d not in search_url and "amazon" not in search_url:
                domain_routing_ok = False
        domain_routing_ok = domain_routing_ok and "AU" in (PRODUCTION_MARKETS or [])
    except Exception as e:
        print(f"domain routing FAIL: {e}")
        domain_routing_ok = False

    # 3) Seed activation: get_activation_targets_for_market returns structured output (may be empty)
    try:
        from amazon_research.scheduler.multi_market_activation import (
            get_activation_targets_for_market,
            ACTIVATION_STATUS_ACTIVATED,
        )
        items = get_activation_targets_for_market("DE", workspace_id=None, limit_category=1, limit_keyword=1)
        seed_activation_ok = isinstance(items, list)
        for it in items:
            seed_activation_ok = seed_activation_ok and "market" in it and "target_type" in it and "target_id" in it and "activation_status" in it and "timestamp" in it
            if not seed_activation_ok:
                break
    except Exception as e:
        print(f"seed activation FAIL: {e}")
        seed_activation_ok = False

    # 4) Scheduler compatibility: to_scheduler_tasks_multi_market and enqueue_multi_market_activation
    try:
        from amazon_research.scheduler.multi_market_activation import (
            to_scheduler_tasks_multi_market,
            enqueue_multi_market_activation,
        )
        fake_targets = [
            {"market": "DE", "target_type": "keyword", "target_id": "smoke_test_kw", "seed_id": None, "activation_status": "activated", "timestamp": "2025-01-01T00:00:00Z"},
            {"market": "US", "target_type": "category", "target_id": "https://www.amazon.com/s", "seed_id": None, "activation_status": "activated", "timestamp": "2025-01-01T00:00:00Z"},
        ]
        tasks = to_scheduler_tasks_multi_market(fake_targets, workspace_id=None)
        scheduler_compat_ok = isinstance(tasks, list) and all(
            t.get("task_type") and (t.get("payload") or {}).get("marketplace") for t in tasks
        )
        # Enqueue with limit 0 to avoid actually enqueueing if no seeds
        result = enqueue_multi_market_activation(markets=["DE"], workspace_id=None, limit_per_type=0)
        scheduler_compat_ok = scheduler_compat_ok and "job_ids" in result and "summary" in result and "activation_targets" in result
    except Exception as e:
        print(f"scheduler compatibility FAIL: {e}")
        scheduler_compat_ok = False

    all_ok = market_separation_ok and domain_routing_ok and seed_activation_ok and scheduler_compat_ok
    print("multi-market crawler activation OK" if all_ok else "multi-market crawler activation FAIL")
    print("market separation: OK" if market_separation_ok else "market separation: FAIL")
    print("domain routing: OK" if domain_routing_ok else "domain routing: FAIL")
    print("seed activation: OK" if seed_activation_ok else "seed activation: FAIL")
    print("scheduler compatibility: OK" if scheduler_compat_ok else "scheduler compatibility: FAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
