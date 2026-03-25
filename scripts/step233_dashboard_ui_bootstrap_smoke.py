#!/usr/bin/env python3
"""
Step 233: Dashboard UI App Bootstrap & Live Workspace Panel – smoke test.
Validates frontend app exists, package.json, vite config, api base config,
dashboard page wiring, and build command readiness.
"""
from pathlib import Path
import subprocess
import sys
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def ok(name: str) -> bool:
    print(f"{name}: OK")
    return True


def fail(name: str, msg: str) -> bool:
    print(f"{name}: FAIL — {msg}", file=sys.stderr)
    return False


def main() -> int:
    results: List[Tuple[str, bool, str]] = []  # (label, passed, error_msg)

    # frontend app exists
    if not FRONTEND.is_dir():
        results.append(("frontend app exists", False, "frontend/ directory missing"))
    else:
        results.append(("frontend app exists", True, ""))

    # package.json exists
    pkg = FRONTEND / "package.json"
    if not pkg.is_file():
        results.append(("package json present", False, "package.json not found"))
    else:
        content = pkg.read_text()
        if "vite" not in content.lower() or "react" not in content.lower():
            results.append(("package json present", False, "package.json missing vite/react"))
        else:
            results.append(("package json present", True, ""))

    # vite config exists
    vite_config = FRONTEND / "vite.config.ts"
    if not vite_config.is_file():
        results.append(("vite config present", False, "vite.config.ts not found"))
    else:
        results.append(("vite config present", True, ""))

    # api base config exists
    env_example = FRONTEND / ".env.example"
    api_ts = FRONTEND / "src" / "lib" / "api.ts"
    vite_env = FRONTEND / "src" / "vite-env.d.ts"
    has_env = env_example.is_file() and "VITE_API_BASE_URL" in (env_example.read_text() if env_example.is_file() else "")
    has_api_ref = api_ts.is_file() and "VITE_API_BASE_URL" in (api_ts.read_text() if api_ts.is_file() else "")
    has_typed = vite_env.is_file() and "VITE_API_BASE_URL" in (vite_env.read_text() if vite_env.is_file() else "")
    if not (has_env or has_api_ref or has_typed):
        results.append(("api base config present", False, "VITE_API_BASE_URL not found"))
    else:
        results.append(("api base config present", True, ""))

    # dashboard page wiring exists
    dashboard_page = FRONTEND / "src" / "pages" / "DashboardPage.tsx"
    if not dashboard_page.is_file():
        results.append(("dashboard page wiring", False, "DashboardPage.tsx not found"))
    else:
        text = dashboard_page.read_text()
        needed = ["api.", "HealthCard", "OverviewCard", "OpportunityList", "PortfolioSummaryCard", "AlertsCard", "StrategySummaryCard"]
        missing = [n for n in needed if n not in text]
        if missing:
            results.append(("dashboard page wiring", False, f"missing: {missing}"))
        else:
            results.append(("dashboard page wiring", True, ""))

    # build command readiness
    if not pkg.is_file():
        results.append(("build command readiness", False, "no package.json"))
    else:
        try:
            r = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(FRONTEND),
                capture_output=True,
                text=True,
                timeout=120,
            )
            if r.returncode != 0:
                results.append(("build command readiness", False, f"exit {r.returncode}: {r.stderr[:300]}"))
            else:
                results.append(("build command readiness", True, ""))
        except FileNotFoundError:
            results.append(("build command readiness", False, "npm not found"))
        except subprocess.TimeoutExpired:
            results.append(("build command readiness", False, "timed out"))

    failed = [(l, m) for l, p, m in results if not p]
    for label, msg in failed:
        print(f"{label}: FAIL — {msg}", file=sys.stderr)

    if failed:
        return 1
    print("dashboard ui bootstrap OK")
    for label, _p, _ in results:
        print(f"{label}: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
