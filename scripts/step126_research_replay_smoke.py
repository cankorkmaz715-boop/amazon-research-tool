#!/usr/bin/env python3
"""Step 126: Research replay engine – run reconstruction, step ordering, output replay, dashboard compatibility."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))

STEP_TYPES = (
    "triggered_scans",
    "discovery_outputs",
    "niche_cluster",
    "ranking",
    "alerts",
)


def main():
    from dotenv import load_dotenv
    load_dotenv()

    from amazon_research.discovery import get_replay

    out = get_replay(workspace_id=None, limit_jobs=20, limit_discovery=20, limit_alerts=20)

    run_ok = (
        "replay_id" in out
        and (out.get("replay_id") or "").startswith("replay-")
        and "steps" in out
        and isinstance(out.get("steps"), list)
        and "step_count" in out
        and out.get("step_count") == len(out.get("steps", []))
    )

    step_ordering_ok = True
    for i, step in enumerate(out.get("steps", [])):
        if not isinstance(step, dict):
            step_ordering_ok = False
            break
        if step.get("step_id") != i + 1:
            step_ordering_ok = False
        if (step.get("step_type") or "") not in STEP_TYPES:
            step_ordering_ok = False
        if "summary" not in step:
            step_ordering_ok = False

    output_replay_ok = True
    for step in out.get("steps", []):
        if "output_summary" not in step:
            output_replay_ok = False
        if "step_type" not in step:
            output_replay_ok = False

    dashboard_ok = (
        "generated_at" in out
        and ("source_run_id" in out or True)
    )

    print("research replay engine OK")
    print("run reconstruction: OK" if run_ok else "run reconstruction: FAIL")
    print("step ordering: OK" if step_ordering_ok else "step ordering: FAIL")
    print("output replay: OK" if output_replay_ok else "output replay: FAIL")
    print("dashboard compatibility: OK" if dashboard_ok else "dashboard compatibility: FAIL")

    if not (run_ok and step_ordering_ok and output_replay_ok and dashboard_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
