#!/bin/bash
# Step 2 verification: Playwright env ready (system deps + Chromium).
# Run from project root with venv active and PYTHONPATH=src.
set -e
echo "=== Step 2: Verify env ==="
echo -n "Playwright module ... "
python3 -c "import playwright; print('OK')"
echo -n "Chromium launch (headless) ... "
python3 -c "
from playwright.sync_api import sync_playwright
p = sync_playwright().start()
b = p.chromium.launch(headless=True)
b.close()
p.stop()
print('OK')
"
echo "=== Step 2 env check passed. ==="
