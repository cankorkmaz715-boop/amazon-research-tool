#!/usr/bin/env python3
"""Step 3 smoke test: proxy config from .env only. No network, no browser."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.config import get_config
from amazon_research.proxy import ProxyManager

def main():
    pm = ProxyManager.from_config()
    if pm.is_enabled():
        cfg = get_config()
        print("proxy enabled")
        print("host:", cfg.proxy_host)
        print("port:", cfg.proxy_port)
    else:
        print("proxy disabled")

if __name__ == "__main__":
    main()
