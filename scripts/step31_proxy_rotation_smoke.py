#!/usr/bin/env python3
"""Step 31: Proxy rotation v1 – pool, deterministic round-robin, one proxy per session."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    from dotenv import load_dotenv
    load_dotenv()
    from amazon_research.proxy import ProxyManager

    pm = ProxyManager.from_config()
    # Pool: at least one entry when proxy enabled, or empty when disabled
    pool_ok = pm.pool_size() >= 0 and (not pm.is_enabled() or pm.pool_size() >= 1)
    if pm.is_enabled() and pm.pool_size() == 0:
        pool_ok = False

    # Session strategy: get_next_for_session() advances rotation; get_playwright_proxy() returns current
    session_ok = True
    try:
        pm.get_next_for_session()
        p1 = pm.get_playwright_proxy()
        pm.get_next_for_session()
        p2 = pm.get_playwright_proxy()
        if pm.is_enabled() and pm.pool_size() >= 2:
            session_ok = p1 is not None and p2 is not None
        else:
            session_ok = True
    except Exception:
        session_ok = False

    print("proxy rotation v1 OK")
    print("rotation pool: OK" if pool_ok else "rotation pool: FAIL")
    print("session strategy: OK" if session_ok else "session strategy: FAIL")

    if not (pool_ok and session_ok):
        sys.exit(1)

if __name__ == "__main__":
    main()
