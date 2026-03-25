#!/usr/bin/env python3
"""
Step 239: Discovery search UI – smoke test.
Validates discovery page wiring, keyword search wiring, market results rendering,
loading/empty/error states, workspace integration, payload-to-UI stability.
"""
from pathlib import Path
import sys
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _ok(name: str) -> tuple[str, bool]:
    return (name, True)


def _fail(name: str, msg: str) -> tuple[str, bool]:
    print(f"{name}: FAIL — {msg}", file=sys.stderr)
    return (name, False)


def _check_discovery_page_wiring() -> tuple[str, bool]:
    """Discovery search page and route exist."""
    page = FRONTEND / "src" / "features" / "discovery" / "DiscoverySearchPage.tsx"
    if not page.is_file():
        return _fail("discovery page wiring", "DiscoverySearchPage.tsx missing")
    content = page.read_text(encoding="utf-8", errors="replace")
    if "DiscoverySearchPage" not in content or "useDiscoverySearch" not in content:
        return _fail("discovery page wiring", "page or hook not found")
    if "data-testid=\"discovery-search-page\"" not in content and "data-testid='discovery-search-page'" not in content:
        return _fail("discovery page wiring", "testid missing")
    return _ok("discovery page wiring")


def _check_keyword_search_wiring() -> tuple[str, bool]:
    """Keyword search bar and API wiring."""
    bar = FRONTEND / "src" / "features" / "discovery" / "DiscoverySearchBar.tsx"
    api = FRONTEND / "src" / "lib" / "api.ts"
    if not bar.is_file():
        return _fail("keyword search wiring", "DiscoverySearchBar.tsx missing")
    if "getDiscoveryKeywords" not in api.read_text(encoding="utf-8", errors="replace"):
        return _fail("keyword search wiring", "getDiscoveryKeywords not in api.ts")
    hook = FRONTEND / "src" / "features" / "discovery" / "useDiscoverySearch.ts"
    if not hook.is_file() or "getDiscoveryKeywords" not in hook.read_text(encoding="utf-8", errors="replace"):
        return _fail("keyword search wiring", "hook not calling keyword API")
    return _ok("keyword search wiring")


def _check_market_results_rendering() -> tuple[str, bool]:
    """Market section and card render market data."""
    section = FRONTEND / "src" / "features" / "discovery" / "DiscoveryMarketSection.tsx"
    card = FRONTEND / "src" / "features" / "discovery" / "DiscoveryResultCard.tsx"
    if not section.is_file():
        return _fail("market results rendering", "DiscoveryMarketSection.tsx missing")
    if not card.is_file():
        return _fail("market results rendering", "DiscoveryResultCard.tsx missing")
    card_text = card.read_text(encoding="utf-8", errors="replace")
    if "MarketResultCard" not in card_text or ("market_key" not in card_text and "discovery_count" not in card_text):
        return _fail("market results rendering", "MarketResultCard or fields missing")
    return _ok("market results rendering")


def _check_loading_empty_error_states() -> tuple[str, bool]:
    """Loading, empty, error state components exist."""
    for name, f in [
        ("DiscoveryLoadingState", "DiscoveryLoadingState.tsx"),
        ("DiscoveryEmptyState", "DiscoveryEmptyState.tsx"),
        ("DiscoveryErrorState", "DiscoveryErrorState.tsx"),
    ]:
        path = FRONTEND / "src" / "features" / "discovery" / f
        if not path.is_file():
            return _fail("loading empty error states", f"{f} missing")
    page_text = (FRONTEND / "src" / "features" / "discovery" / "DiscoverySearchPage.tsx").read_text(encoding="utf-8", errors="replace")
    if "DiscoveryLoadingState" not in page_text or "DiscoveryErrorState" not in page_text:
        return _fail("loading empty error states", "page does not use loading or error state")
    if "DiscoveryResultsList" not in page_text:
        return _fail("loading empty error states", "page does not use results list")
    return _ok("loading empty error states")


def _check_workspace_integration_compatibility() -> tuple[str, bool]:
    """App includes discovery and workspace context."""
    app = FRONTEND / "src" / "App.tsx"
    text = app.read_text(encoding="utf-8", errors="replace")
    if "DiscoverySearchPage" not in text or "discovery" not in text.lower():
        return _fail("workspace integration compatibility", "App does not render Discovery")
    if "workspaceId" not in text:
        return _fail("workspace integration compatibility", "workspaceId not passed")
    return _ok("workspace integration compatibility")


def _check_payload_to_ui_stability() -> tuple[str, bool]:
    """Types and components handle API payload shape."""
    types = FRONTEND / "src" / "types" / "api.ts"
    text = types.read_text(encoding="utf-8", errors="replace")
    if "DiscoveryKeywordItem" not in text or "DiscoveryMarketItem" not in text:
        return _fail("payload to UI stability", "discovery types missing in api.ts")
    list_comp = FRONTEND / "src" / "features" / "discovery" / "DiscoveryResultsList.tsx"
    if not list_comp.is_file():
        return _fail("payload to UI stability", "DiscoveryResultsList missing")
    list_text = list_comp.read_text(encoding="utf-8", errors="replace")
    if "keywordResults" not in list_text or "marketResults" not in list_text:
        return _fail("payload to UI stability", "results list does not accept keyword/market results")
    return _ok("payload to UI stability")


def _check_build() -> tuple[str, bool]:
    """Frontend build succeeds."""
    try:
        subprocess.run(
            ["npm", "run", "build"],
            cwd=FRONTEND,
            check=True,
            capture_output=True,
            timeout=120,
        )
        return _ok("build")
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        return _fail("payload to UI stability", f"build failed: {e}")


def main() -> int:
    checks = [
        _check_discovery_page_wiring,
        _check_keyword_search_wiring,
        _check_market_results_rendering,
        _check_loading_empty_error_states,
        _check_workspace_integration_compatibility,
        _check_payload_to_ui_stability,
    ]
    results: list[tuple[str, bool]] = []
    for check in checks:
        results.append(check())
    if all(r[1] for r in results):
        print("discovery search UI OK")
        for name, _ in results:
            print(f"{name}: OK")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
