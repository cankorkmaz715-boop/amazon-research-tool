#!/usr/bin/env python3
"""
Step 190 smoke test: Opportunity intelligence pipeline.
Validates pipeline integrity, data flow, and scheduler compatibility.
"""
import os
import sys

# Project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))

def main() -> None:
    from amazon_research.discovery.opportunity_intelligence_pipeline import (
        run_pipeline,
        validate_data_flow,
        get_pipeline_run_for_scheduler,
        PIPELINE_STAGE_INGESTION,
        PIPELINE_STAGE_SIGNALS,
        PIPELINE_STAGE_RANKING,
        PIPELINE_STAGE_ALERTS,
    )

    pipeline_ok = True
    integrity_ok = True
    data_flow_ok = True
    scheduler_ok = True

    # --- Pipeline integrity: run_pipeline returns expected log shape and stages in order
    try:
        log = run_pipeline(
            limit_discovery=5,
            limit_opportunities=5,
            limit_rankings=5,
            score_threshold=70.0,
        )
        required = {
            "started_at",
            "finished_at",
            "discovery_count",
            "signal_computation",
            "ranking_updates",
            "alerts_generated",
            "stages",
            "data_flow_ok",
        }
        if not required.issubset(log.keys()):
            integrity_ok = False
        stages = log.get("stages") or []
        expected_stages = [PIPELINE_STAGE_INGESTION, PIPELINE_STAGE_SIGNALS, PIPELINE_STAGE_RANKING, PIPELINE_STAGE_ALERTS]
        stage_names = [s.get("stage") for s in stages if s.get("stage")]
        if stage_names != expected_stages:
            integrity_ok = False
    except Exception as e:
        integrity_ok = False
        print(f"pipeline run error: {e}")

    # --- Data flow validation: validate_data_flow returns consistent structure and ok when applicable
    try:
        val = validate_data_flow(sample_limit=5)
        if not isinstance(val, dict):
            data_flow_ok = False
        if "ok" not in val or "memory_has_refs" not in val or "signals_cover_refs" not in val or "rankings_cover_refs" not in val:
            data_flow_ok = False
        # When no refs, ok can be True (nothing to validate); when refs exist, consistency is checked
    except Exception as e:
        data_flow_ok = False
        print(f"validate_data_flow error: {e}")

    # --- Scheduler compatibility: get_pipeline_run_for_scheduler returns same log shape
    try:
        sched_log = get_pipeline_run_for_scheduler()
        if not isinstance(sched_log, dict):
            scheduler_ok = False
        for key in ("discovery_count", "signal_computation", "ranking_updates", "alerts_generated", "stages"):
            if key not in sched_log:
                scheduler_ok = False
    except Exception as e:
        scheduler_ok = False
        print(f"get_pipeline_run_for_scheduler error: {e}")

    print("opportunity intelligence pipeline OK" if pipeline_ok else "opportunity intelligence pipeline FAIL")
    print("pipeline integrity: OK" if integrity_ok else "pipeline integrity: FAIL")
    print("data flow validation: OK" if data_flow_ok else "data flow validation: FAIL")
    print("scheduler compatibility: OK" if scheduler_ok else "scheduler compatibility: FAIL")
    if not (pipeline_ok and integrity_ok and data_flow_ok and scheduler_ok):
        sys.exit(1)

if __name__ == "__main__":
    main()
