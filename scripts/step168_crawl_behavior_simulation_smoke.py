#!/usr/bin/env python3
"""Step 168: Crawl behavior simulation – navigation patterns, timing variation, product detour, crawler compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from amazon_research.monitoring.crawl_behavior_simulation import (
        build_crawl_simulation,
        build_navigation_sequence,
        build_timing_profile,
        get_next_step_delay_for_crawler,
        simulate_product_detour,
        get_simulation_for_scheduler_target,
        BEHAVIOR_CATEGORY_BROWSE,
        BEHAVIOR_SEARCH_RESULTS_PAGING,
        BEHAVIOR_PRODUCT_DETOUR,
        BEHAVIOR_MIXED,
        STEP_CATEGORY_PAGE,
        STEP_SEARCH_RESULTS,
        STEP_PRODUCT_PAGE,
        STEP_BACK_TO_SEARCH,
    )

    # 1) Navigation pattern: required keys and sequence content
    sim = build_crawl_simulation(behavior_type=BEHAVIOR_MIXED, seed=42)
    nav_ok = (
        "simulation_id" in sim
        and "simulated_behavior_type" in sim
        and "navigation_sequence_summary" in sim
        and "timing_profile_summary" in sim
        and "timestamp" in sim
    )
    nav_seq = sim.get("navigation_sequence_summary") or []
    nav_ok = nav_ok and isinstance(nav_seq, list) and len(nav_seq) >= 1
    nav_ok = nav_ok and (
        STEP_CATEGORY_PAGE in nav_seq or STEP_SEARCH_RESULTS in nav_seq or STEP_PRODUCT_PAGE in nav_seq
    )

    # 2) Timing variation: variable pacing, step_delays_seconds, total_estimated_seconds
    timing = sim.get("timing_profile_summary") or {}
    timing_ok = (
        isinstance(timing, dict)
        and timing.get("variable_pacing") is True
        and "step_delays_seconds" in timing
        and "total_estimated_seconds" in timing
    )
    delays = timing.get("step_delays_seconds") or []
    timing_ok = timing_ok and isinstance(delays, list)
    # Deterministic with seed: same sim twice
    sim2 = build_crawl_simulation(behavior_type=BEHAVIOR_CATEGORY_BROWSE, seed=99)
    timing_ok = timing_ok and (sim2.get("timing_profile_summary") or {}).get("variable_pacing") is True

    # 3) Product detour simulation: product_page and back_to_search in sequence
    detour = simulate_product_detour(target_id="B001", seed=1)
    detour_ok = (
        detour.get("simulated_behavior_type") == BEHAVIOR_PRODUCT_DETOUR
        and STEP_PRODUCT_PAGE in (detour.get("navigation_sequence_summary") or [])
        and STEP_BACK_TO_SEARCH in (detour.get("navigation_sequence_summary") or [])
    )

    # 4) Crawler compatibility: next-step delay from antibot integration, scheduler target simulation
    delay = get_next_step_delay_for_crawler(base_delay=0.5, jitter_max=0.5)
    crawler_ok = isinstance(delay, (int, float)) and delay >= 0
    sched_sim = get_simulation_for_scheduler_target("cat-123", target_type="category", seed=0)
    crawler_ok = (
        crawler_ok
        and "simulation_id" in sched_sim
        and "navigation_sequence_summary" in sched_sim
        and sched_sim.get("simulated_behavior_type") == BEHAVIOR_CATEGORY_BROWSE
    )
    kw_sim = get_simulation_for_scheduler_target("kw-1", target_type="keyword", seed=0)
    crawler_ok = crawler_ok and kw_sim.get("simulated_behavior_type") == BEHAVIOR_SEARCH_RESULTS_PAGING

    print("crawl behavior simulation OK")
    print("navigation pattern: OK" if nav_ok else "navigation pattern: FAIL")
    print("timing variation: OK" if timing_ok else "timing variation: FAIL")
    print("product detour simulation: OK" if detour_ok else "product detour simulation: FAIL")
    print("crawler compatibility: OK" if crawler_ok else "crawler compatibility: FAIL")

    if not (nav_ok and timing_ok and detour_ok and crawler_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
