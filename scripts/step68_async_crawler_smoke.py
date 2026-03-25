#!/usr/bin/env python3
"""Step 68: Async crawler foundation v1 – async abstraction, sync compatibility, worker readiness."""
import asyncio
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.crawler import get_async_crawler, run_refresh_async
    from amazon_research.bots import DataRefreshBot

    # --- Async abstraction: await run_refresh_async([]) returns 0, no sync Playwright in event loop ---
    async def _check_async():
        out = await run_refresh_async([], workspace_id=None)
        return out

    try:
        result = asyncio.run(_check_async())
        async_ok = result == 0
    except Exception as e:
        async_ok = False
        print("async check error:", e, file=sys.stderr)

    # --- Sync compatibility: existing sync bot still works ---
    try:
        sync_result = DataRefreshBot().run(asin_list=[], workspace_id=None)
        sync_ok = sync_result == 0
    except Exception as e:
        sync_ok = False
        print("sync check error:", e, file=sys.stderr)

    # --- Worker readiness: async crawler has run_discovery_async and run_refresh_async (callable, return coroutines) ---
    crawler = get_async_crawler()
    worker_ok = (
        hasattr(crawler, "run_discovery_async")
        and hasattr(crawler, "run_refresh_async")
        and asyncio.iscoroutinefunction(crawler.run_discovery_async)
        and asyncio.iscoroutinefunction(crawler.run_refresh_async)
    )

    print("async crawler foundation v1 OK")
    print("async abstraction: OK" if async_ok else "async abstraction: FAIL")
    print("sync compatibility: OK" if sync_ok else "sync compatibility: FAIL")
    print("worker readiness: OK" if worker_ok else "worker readiness: FAIL")

    if not (async_ok and sync_ok and worker_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
