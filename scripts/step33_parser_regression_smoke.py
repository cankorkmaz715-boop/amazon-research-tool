#!/usr/bin/env python3
"""Step 33: Parser regression – fixture-based tests for discovery and refresh parsers. Runs regression in subprocess."""
import os
import sys
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

def main():
    runner = os.path.join(ROOT, "scripts", "step33_parser_regression_runner.py")
    if not os.path.isfile(runner):
        print("parser regression OK")
        print("discovery fixtures: FAIL (runner missing)")
        print("refresh fixtures: FAIL (runner missing)")
        sys.exit(1)
    proc = subprocess.run(
        [sys.executable, runner],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "PYTHONPATH": os.path.join(ROOT, "src")},
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    discovery_ok = "discovery fixtures: OK" in out
    refresh_ok = "refresh fixtures: OK" in out
    print("parser regression OK")
    print("discovery fixtures: OK" if discovery_ok else "discovery fixtures: FAIL")
    print("refresh fixtures: OK" if refresh_ok else "refresh fixtures: FAIL")
    if not (discovery_ok and refresh_ok):
        if out.strip():
            sys.stderr.write(out)
        sys.exit(1)

if __name__ == "__main__":
    main()
