#!/usr/bin/env python3
"""Step 123: Continuous opportunity discovery loop – trigger integration, scan execution, opportunity and alert generation, cycle output."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import run_opportunity_discovery_cycle

    result = run_opportunity_discovery_cycle(
        workspace_id=None,
        marketplace="DE",
        max_enqueue=3,
        max_trigger_eval=10,
        include_intelligent_plan=True,
    )

    trigger_ok = (
        "cycle_id" in result
        and "triggered_scans" in result
        and "timestamp" in result
    )

    scan_ok = isinstance(result.get("triggered_scans"), list)
    for s in result.get("triggered_scans") or []:
        scan_ok = scan_ok and "job_id" in s and "job_type" in s

    opportunity_ok = isinstance(result.get("ranked_opportunities"), list)

    alert_ok = isinstance(result.get("generated_alerts"), list)

    cycle_ok = (
        "cycle_id" in result
        and "discovered_candidates" in result
        and "ranked_opportunities" in result
        and "generated_alerts" in result
        and "timestamp" in result
    )

    print("continuous opportunity discovery loop OK")
    print("trigger integration: OK" if trigger_ok else "trigger integration: FAIL")
    print("scan execution: OK" if scan_ok else "scan execution: FAIL")
    print("opportunity generation: OK" if opportunity_ok else "opportunity generation: FAIL")
    print("alert generation: OK" if alert_ok else "alert generation: FAIL")
    print("cycle output: OK" if cycle_ok else "cycle output: FAIL")

    if not (trigger_ok and scan_ok and opportunity_ok and alert_ok and cycle_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
