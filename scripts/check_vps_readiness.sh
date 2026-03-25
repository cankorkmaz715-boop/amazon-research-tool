#!/bin/bash
# Minimal server readiness test – Amazon Research Tool
# Run from project root. Activate venv first if you use one:
#   source .venv/bin/activate
#   export PYTHONPATH="$(pwd)/src"
#   bash scripts/check_vps_readiness.sh

set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
echo "=== VPS Readiness Check ==="

echo -n "Python 3.10+ ... "
python3 --version
python3 -c "import sys; assert sys.version_info >= (3, 10), 'Need Python 3.10+'"
echo "OK"

echo -n "venv ... "
python3 -m venv --help > /dev/null 2>&1 && echo "OK" || { echo "MISSING"; exit 1; }

echo -n "pip ... "
python3 -m pip --version > /dev/null 2>&1 && echo "OK" || { echo "MISSING"; exit 1; }

echo -n ".env exists ... "
[ -f .env ] && echo "OK" || { echo "MISSING (copy .env.example to .env, set DATABASE_URL)"; exit 1; }

echo -n "DATABASE_URL set ... "
VAL=$(grep -E '^DATABASE_URL=' .env 2>/dev/null | cut -d= -f2-)
[ -n "$VAL" ] && echo "OK" || { echo "MISSING or empty"; exit 1; }

echo -n "Project run (skeleton) ... "
export PYTHONPATH="${PYTHONPATH:-$ROOT/src}"
python3 -m amazon_research.main > /tmp/amazon_readiness.log 2>&1
grep -q "skeleton run complete" /tmp/amazon_readiness.log && echo "OK" || { echo "FAIL"; cat /tmp/amazon_readiness.log; exit 1; }

echo "=== All checks passed. Server is ready for next step (proxy + Playwright base). ==="
