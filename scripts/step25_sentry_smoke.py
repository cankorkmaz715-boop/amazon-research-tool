#!/usr/bin/env python3
"""Step 25: Sentry integration readiness – optional init from SENTRY_DSN; no secrets in output."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

from dotenv import load_dotenv
load_dotenv()

# Ensure we don't accidentally have DSN in env for this smoke run
os.environ.pop("SENTRY_DSN", None)

from amazon_research.monitoring import init_sentry, sentry_status

def main():
    init_sentry()
    status = sentry_status()
    print("sentry readiness OK")
    print("sentry:", status)

if __name__ == "__main__":
    main()
