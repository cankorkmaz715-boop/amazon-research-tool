#!/usr/bin/env python3
"""Step 4 smoke test: Playwright browser layer. Launches headless, one page, no real sites."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.browser import BrowserSession

def main():
    with BrowserSession(headless=True) as session:
        page = session.get_page()
        if page is None:
            print("FAIL: no page")
            sys.exit(1)
        page.goto("about:blank")
        title = page.title()
    print("browser layer OK")
    print("page title:", title)

if __name__ == "__main__":
    main()
