#!/usr/bin/env python3
"""Step 21: Anti-bot hardening – session reuse, randomized delays, navigation retry with backoff."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

def main():
    from amazon_research.browser import BrowserSession
    from amazon_research.config import get_config

    cfg = get_config()
    assert cfg.antibot_delay_min_sec >= 2.0 and cfg.antibot_delay_max_sec <= 10.0
    assert cfg.navigation_retries >= 1

    # One session, multiple navigations (session reuse) + delay + retry
    session = BrowserSession(headless=True)
    session.start()
    try:
        page = session.get_page()
        if not page:
            print("No page")
            sys.exit(1)
        session.goto_with_retry("about:blank", wait_until="domcontentloaded")
        session.delay_between_actions()
        session.goto_with_retry("about:blank", wait_until="domcontentloaded")
    finally:
        session.close()

    print("antibot hardening OK")
    print("browser session reused")
    print("delays active")
    print("retry system active")

if __name__ == "__main__":
    main()
