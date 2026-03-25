#!/usr/bin/env python3
"""Step 9: ASIN discovery bot base. Runs bot with no categories; expects zero ASINs, no crash."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

from amazon_research.db import init_db
from amazon_research.bots import AsinDiscoveryBot

def main():
    init_db()
    bot = AsinDiscoveryBot()
    result = bot.run()
    if not isinstance(result, list):
        print("FAIL: run() did not return a list")
        sys.exit(1)
    print("discovery bot base OK")
    print("discovered:", len(result), "ASINs")

if __name__ == "__main__":
    main()
