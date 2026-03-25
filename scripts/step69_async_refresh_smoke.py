#!/usr/bin/env python3
"""Step 69: Async refresh path v1 – async refresh execution, sync compatibility, worker readiness."""
import asyncio
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.crawler import run_refresh_batch_async
    from amazon_research.bots import DataRefreshBot
    from amazon_research.db import run_job_async

    # --- Async refresh execution: run_refresh_batch_async([]) returns 0 ---
    async def _async_refresh():
        return await run_refresh_batch_async([], workspace_id=None)

    try:
        result = asyncio.run(_async_refresh())
        async_ok = result == 0
    except Exception as e:
        async_ok = False
        print("async refresh error:", e, file=sys.stderr)

    # --- Sync compatibility: existing sync refresh still works ---
    try:
        sync_result = DataRefreshBot().run(asin_list=[], workspace_id=None)
        sync_ok = sync_result == 0
    except Exception as e:
        sync_ok = False
        print("sync refresh error:", e, file=sys.stderr)

    # --- Worker readiness: run_job_async exists and is a coroutine function ---
    worker_ok = asyncio.iscoroutinefunction(run_job_async)

    print("async refresh path v1 OK")
    print("async refresh execution: OK" if async_ok else "async refresh execution: FAIL")
    print("sync compatibility: OK" if sync_ok else "sync compatibility: FAIL")
    print("worker readiness: OK" if worker_ok else "worker readiness: FAIL")

    if not (async_ok and sync_ok and worker_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
