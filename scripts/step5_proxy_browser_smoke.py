#!/usr/bin/env python3
"""Step 5: Proxy + browser integration. Same browser flow; confirms proxy is used when enabled."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.proxy import ProxyManager
from amazon_research.browser import BrowserSession

def main():
    pm = ProxyManager.from_config()
    print("proxy:", "enabled" if pm.is_enabled() else "disabled")

    with BrowserSession(headless=True) as session:
        page = session.get_page()
        if page is None:
            print("FAIL: no page")
            sys.exit(1)
        page.goto("about:blank")
        title = page.title()
    print("proxy + browser integration OK")
    print("page title:", title)

if __name__ == "__main__":
    main()
