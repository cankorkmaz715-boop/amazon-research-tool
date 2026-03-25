#!/usr/bin/env python3
"""
Step 3 verification: central proxy manager loads from config and returns
Playwright-shaped proxy dict when credentials are set. No network calls.
Run from project root with venv active and PYTHONPATH=src.
"""
import os
import sys

# Project root and .env
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
from dotenv import load_dotenv
load_dotenv()

from amazon_research.proxy import ProxyManager

def main():
    pm = ProxyManager.from_config()
    print("Proxy enabled:", pm.is_enabled())
    pw = pm.get_playwright_proxy()
    if pw:
        print("Playwright proxy server:", pw.get("server"))
        print("Username set:", "yes" if pw.get("username") else "no")
        print("Password set:", "yes" if pw.get("password") else "no")
    else:
        print("Playwright proxy: None (proxy disabled)")
    print("Step 3 proxy manager check done.")

if __name__ == "__main__":
    main()
