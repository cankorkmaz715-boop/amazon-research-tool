"""
Async refresh path v1. Step 69 – async-compatible refresh execution; reuses async crawler foundation.
"""
from __future__ import annotations

from typing import List, Optional

from amazon_research.logging_config import get_logger

from .async_foundation import get_async_crawler

logger = get_logger("crawler.refresh_async")


async def run_refresh_batch_async(
    asin_list: List[str],
    workspace_id: Optional[int] = None,
) -> int:
    """
    Async refresh execution path: refresh metrics for the given ASINs.
    Uses the async crawler foundation (no sync Playwright in asyncio loop).
    Returns count of updated ASINs.
    """
    crawler = get_async_crawler()
    return await crawler.run_refresh_async(asin_list=asin_list or [], workspace_id=workspace_id)


async def execute_plan_batch_async(
    plan: dict,
    batch_index: int = 0,
    workspace_id: Optional[int] = None,
) -> int:
    """
    Run one batch from a refresh plan (from planner.build_refresh_plan).
    Queue- and worker-friendly: each batch can be executed via this path.
    """
    batches = plan.get("batches") or []
    if batch_index < 0 or batch_index >= len(batches):
        return 0
    asin_list = batches[batch_index]
    return await run_refresh_batch_async(asin_list=asin_list, workspace_id=workspace_id)
