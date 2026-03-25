"""
Async crawler foundation v1. Step 68 – lightweight async abstraction; no sync Playwright in asyncio loop.
Bridge runs existing sync bots in a thread via asyncio.to_thread() for async compatibility.
"""
from __future__ import annotations

import asyncio
from typing import List, Optional, Protocol, runtime_checkable

from amazon_research.logging_config import get_logger

logger = get_logger("crawler.async_foundation")


@runtime_checkable
class AsyncCrawlerProtocol(Protocol):
    """
    Async-compatible crawler interface for future discovery/refresh execution.
    Implementations may use async Playwright or bridge to sync in a thread.
    """

    async def run_discovery_async(
        self,
        urls: Optional[List[str]] = None,
        workspace_id: Optional[int] = None,
    ) -> List[str]:
        """Discover ASINs from listing URLs. Returns list of ASIN strings."""
        ...

    async def run_refresh_async(
        self,
        asin_list: List[str],
        workspace_id: Optional[int] = None,
    ) -> int:
        """Refresh metrics for given ASINs. Returns count of updated ASINs."""
        ...


class ThreadedAsyncCrawler:
    """
    Runs existing sync discovery/refresh in a thread so async callers never run sync Playwright
    inside the asyncio event loop. Backward compatible with current sync architecture.
    """

    async def run_discovery_async(
        self,
        urls: Optional[List[str]] = None,
        workspace_id: Optional[int] = None,
    ) -> List[str]:
        def _sync() -> List[str]:
            from amazon_research.bots import AsinDiscoveryBot
            bot = AsinDiscoveryBot()
            result = bot.run(urls=urls, workspace_id=workspace_id)
            return result if isinstance(result, list) else []

        return await asyncio.to_thread(_sync)

    async def run_refresh_async(
        self,
        asin_list: List[str],
        workspace_id: Optional[int] = None,
    ) -> int:
        def _sync() -> int:
            from amazon_research.bots import DataRefreshBot
            bot = DataRefreshBot()
            return bot.run(asin_list=asin_list or [], workspace_id=workspace_id)

        return await asyncio.to_thread(_sync)


_default_crawler: Optional[ThreadedAsyncCrawler] = None


def get_async_crawler() -> AsyncCrawlerProtocol:
    """Return the default async-capable crawler (thread bridge). Worker-ready for future async loops."""
    global _default_crawler
    if _default_crawler is None:
        _default_crawler = ThreadedAsyncCrawler()
    return _default_crawler


async def run_discovery_async(
    urls: Optional[List[str]] = None,
    workspace_id: Optional[int] = None,
) -> List[str]:
    """Convenience: run discovery via default async crawler."""
    return await get_async_crawler().run_discovery_async(urls=urls, workspace_id=workspace_id)


async def run_refresh_async(
    asin_list: List[str],
    workspace_id: Optional[int] = None,
) -> int:
    """Convenience: run refresh via default async crawler."""
    return await get_async_crawler().run_refresh_async(asin_list=asin_list, workspace_id=workspace_id)
