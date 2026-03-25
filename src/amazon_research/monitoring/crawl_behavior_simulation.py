"""
Step 168: Crawl behavior simulation – realistic human-like crawl flows.
Browsing category pages, search result paging, product detours, variable pacing, short pauses.
Integrates with anti-bot hardening, scraper reliability, intelligent crawl scheduler.
Does not rewrite core discovery or refresh logic. Lightweight, extensible.
"""
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.crawl_behavior_simulation")

# Simulated behavior types
BEHAVIOR_CATEGORY_BROWSE = "category_browse"
BEHAVIOR_SEARCH_RESULTS_PAGING = "search_results_paging"
BEHAVIOR_PRODUCT_DETOUR = "product_detour"
BEHAVIOR_MIXED = "mixed"

# Navigation step labels
STEP_CATEGORY_PAGE = "category_page"
STEP_SEARCH_RESULTS = "search_results_page"
STEP_PRODUCT_PAGE = "product_page"
STEP_BACK_TO_SEARCH = "back_to_search"
STEP_PAUSE = "pause"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_step_delay(base: float = 0.8, jitter_max: float = 1.5) -> float:
    """Variable pacing: base + random jitter. Uses local random for determinism when seeded."""
    return round(base + random.uniform(0, jitter_max), 2)


def build_navigation_sequence(
    behavior_type: str,
    category_pages: int = 2,
    search_pages: int = 2,
    include_product_detour: bool = True,
    seed: Optional[int] = None,
) -> List[str]:
    """
    Build a human-like navigation sequence. Optionally seed for reproducible tests.
    Returns list of step labels (e.g. category_page, search_results_page, product_page, back_to_search).
    """
    if seed is not None:
        random.seed(seed)
    steps: List[str] = []
    if behavior_type == BEHAVIOR_CATEGORY_BROWSE:
        for _ in range(max(1, category_pages)):
            steps.append(STEP_CATEGORY_PAGE)
            steps.append(STEP_PAUSE)
    elif behavior_type == BEHAVIOR_SEARCH_RESULTS_PAGING:
        for i in range(max(1, search_pages)):
            steps.append(STEP_SEARCH_RESULTS if i == 0 else f"{STEP_SEARCH_RESULTS}_{i + 1}")
            steps.append(STEP_PAUSE)
    elif behavior_type == BEHAVIOR_PRODUCT_DETOUR:
        steps.append(STEP_SEARCH_RESULTS)
        steps.append(STEP_PAUSE)
        steps.append(STEP_PRODUCT_PAGE)
        steps.append(STEP_PAUSE)
        steps.append(STEP_BACK_TO_SEARCH)
    elif behavior_type == BEHAVIOR_MIXED:
        for _ in range(max(1, category_pages)):
            steps.append(STEP_CATEGORY_PAGE)
            steps.append(STEP_PAUSE)
        for i in range(max(1, search_pages)):
            steps.append(STEP_SEARCH_RESULTS if i == 0 else f"{STEP_SEARCH_RESULTS}_{i + 1}")
            steps.append(STEP_PAUSE)
        if include_product_detour:
            steps.append(STEP_PRODUCT_PAGE)
            steps.append(STEP_PAUSE)
            steps.append(STEP_BACK_TO_SEARCH)
    else:
        for _ in range(max(1, category_pages)):
            steps.append(STEP_CATEGORY_PAGE)
            steps.append(STEP_PAUSE)
        for i in range(max(1, search_pages)):
            steps.append(STEP_SEARCH_RESULTS if i == 0 else f"{STEP_SEARCH_RESULTS}_{i + 1}")
            steps.append(STEP_PAUSE)
        if include_product_detour:
            steps.append(STEP_PRODUCT_PAGE)
            steps.append(STEP_PAUSE)
            steps.append(STEP_BACK_TO_SEARCH)
    if steps and steps[-1] == STEP_PAUSE and len(steps) > 1:
        steps = steps[:-1]
    return steps


def build_timing_profile(
    navigation_sequence: List[str],
    base_delay: float = 0.8,
    jitter_max: float = 1.5,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build variable pacing: short pauses between steps. Uses anti-bot jitter when available.
    Returns timing_profile_summary with step_delays_seconds, total_estimated_seconds, variable_pacing.
    """
    if seed is not None:
        random.seed(seed)
    delays: List[float] = []
    for i, step in enumerate(navigation_sequence):
        if step == STEP_PAUSE:
            delays.append(_get_step_delay(base=base_delay, jitter_max=jitter_max))
        else:
            # Short pause before each navigation step
            delays.append(_get_step_delay(base=base_delay * 0.5, jitter_max=jitter_max * 0.5))
    total = round(sum(delays), 2)
    return {
        "step_delays_seconds": delays,
        "total_estimated_seconds": total,
        "variable_pacing": True,
    }


def build_crawl_simulation(
    behavior_type: Optional[str] = None,
    target_id: Optional[str] = None,
    seed: Optional[int] = None,
    include_product_detour: bool = True,
    category_pages: int = 2,
    search_pages: int = 2,
) -> Dict[str, Any]:
    """
    Produce one simulation run with simulation_id, simulated_behavior_type, navigation_sequence_summary,
    timing_profile_summary, timestamp. Integrates with anti-bot by using variable pacing.
    """
    if seed is not None:
        random.seed(seed)
    sim_id = str(uuid.uuid4())[:12]
    behavior = behavior_type or (BEHAVIOR_MIXED if include_product_detour else BEHAVIOR_CATEGORY_BROWSE)
    nav = build_navigation_sequence(
        behavior_type=behavior,
        category_pages=category_pages,
        search_pages=search_pages,
        include_product_detour=include_product_detour,
        seed=seed,
    )
    timing = build_timing_profile(nav, seed=seed)
    out: Dict[str, Any] = {
        "simulation_id": sim_id,
        "simulated_behavior_type": behavior,
        "navigation_sequence_summary": nav,
        "timing_profile_summary": timing,
        "timestamp": _now_iso(),
    }
    if target_id:
        out["target_id"] = target_id
    return out


def get_next_step_delay_for_crawler(
    base_delay: float = 0.8,
    jitter_max: float = 1.5,
) -> float:
    """
    Return delay in seconds for the next crawl step. Integrates with anti-bot request jitter
    when available; otherwise uses local variable pacing. Crawler execution flow can call this
    between navigation steps.
    """
    try:
        from amazon_research.monitoring.antibot_hardening import get_request_jitter_delay
        return round(get_request_jitter_delay(base_delay=base_delay, jitter_max=jitter_max), 2)
    except Exception:
        return _get_step_delay(base=base_delay, jitter_max=jitter_max)


def simulate_product_detour(
    target_id: Optional[str] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Simulate open product page then return to search. Returns same structure as build_crawl_simulation
    with behavior_type product_detour and sequence: search_results -> product_page -> back_to_search.
    """
    return build_crawl_simulation(
        behavior_type=BEHAVIOR_PRODUCT_DETOUR,
        target_id=target_id or "",
        seed=seed,
        include_product_detour=True,
        category_pages=1,
        search_pages=1,
    )


def get_simulation_for_scheduler_target(
    target_id: str,
    target_type: Optional[str] = None,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a crawl simulation suitable for a target from the intelligent crawl scheduler.
    Chooses behavior type from target_type (category -> category_browse, keyword -> search_results_paging, etc.).
    """
    behavior = BEHAVIOR_MIXED
    if target_type == "category":
        behavior = BEHAVIOR_CATEGORY_BROWSE
    elif target_type == "keyword":
        behavior = BEHAVIOR_SEARCH_RESULTS_PAGING
    elif target_type == "asin_refresh":
        behavior = BEHAVIOR_PRODUCT_DETOUR
    return build_crawl_simulation(
        behavior_type=behavior,
        target_id=target_id,
        seed=seed,
        include_product_detour=(behavior == BEHAVIOR_MIXED or behavior == BEHAVIOR_PRODUCT_DETOUR),
    )
