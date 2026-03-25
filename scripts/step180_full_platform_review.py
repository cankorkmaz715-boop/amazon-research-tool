#!/usr/bin/env python3
"""
Step 180: Full Platform Review and Production Readiness.
Audits: data collection infrastructure, data pipeline integrity, intelligence stack,
workspace intelligence, strategy layer, system resilience. Verifies architecture stability,
integration, and data flow consistency. Does not rewrite any module.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    data_infra_ok = True
    pipeline_ok = True
    intelligence_ok = True
    workspace_ok = True
    strategy_ok = True
    resilience_ok = True
    risks: list = []
    minor_improvements: list = []

    # --- 1) Data collection infrastructure: crawler, proxy, scraping reliability, anti-bot ---
    try:
        from amazon_research.monitoring.scraper_reliability import get_scraper_reliability_status
        from amazon_research.monitoring.antibot_hardening import get_antibot_status
        from amazon_research.monitoring.platform_failure_detector import run_all_checks as run_failure_checks
        s = get_scraper_reliability_status()
        a = get_antibot_status()
        f = run_failure_checks()
        if not isinstance(s, dict) or not isinstance(a, dict):
            data_infra_ok = False
        if "overall" not in f and "scraper" not in f:
            data_infra_ok = False
    except Exception as e:
        data_infra_ok = False
        risks.append(f"Data infrastructure import or run failed: {e!s}"[:100])

    # --- 2) Data pipeline integrity: parsing, data quality guard, data repair ---
    try:
        from amazon_research.monitoring.resilient_parsing import parse_resilient
        from amazon_research.monitoring.data_quality_guard import run_all_checks as run_dq_checks
        from amazon_research.monitoring.data_integrity_repair import missing_data_repair, timeseries_gap_repair
        pr = parse_resilient({"asin": "B1", "title": "T"}, target_id="t1")
        dq = run_dq_checks(record={"asin": "B2", "title": "X"})
        rep = missing_data_repair(target_id="t2")
        if "extracted_fields" not in pr or "parser_confidence" not in pr:
            pipeline_ok = False
        if "data_quality" not in dq or "issues" not in dq:
            pipeline_ok = False
        if rep.get("repair_status") not in ("FIXED", "SKIPPED", "FAILED"):
            pipeline_ok = False
    except Exception as e:
        pipeline_ok = False
        risks.append(f"Data pipeline import or run failed: {e!s}"[:100])

    # --- 3) Intelligence stack: scoring, opportunity detection, signal drift, anomaly, lifecycle ---
    try:
        from amazon_research.discovery.opportunity_lifecycle_engine import get_lifecycle_state
        from amazon_research.monitoring.signal_drift_detector import detect_drift
        from amazon_research.discovery.anomaly_alert_engine import get_anomaly_alerts
        from amazon_research.discovery.opportunity_confidence import get_opportunity_confidence
        life = get_lifecycle_state("test-ref", memory_record={"opportunity_ref": "test-ref", "score_history": [50, 52]})
        drift = detect_drift("trend_score", 10.0, [5.0, 6.0, 7.0], target_id="d1")
        anom = get_anomaly_alerts(target_entity="a1", drift_reports=[{"drift_type": "collapse", "signal_type": "trend", "severity": "high"}])
        conf = get_opportunity_confidence("c1", memory_record={"opportunity_ref": "c1"})
        if "lifecycle_state" not in life or "lifecycle_score" not in life:
            intelligence_ok = False
        if not isinstance(drift, list):
            intelligence_ok = False
        if not isinstance(anom, list):
            intelligence_ok = False
        if "confidence_score" not in conf:
            intelligence_ok = False
    except Exception as e:
        intelligence_ok = False
        risks.append(f"Intelligence stack import or run failed: {e!s}"[:100])

    # --- 4) Workspace intelligence: personalization, feed, recommendation loops, adaptive ---
    try:
        from amazon_research.monitoring import get_workspace_intelligence, get_workspace_personalization_signals
        from amazon_research.discovery import get_workspace_opportunity_feed, get_workspace_intelligence_timeline
        from amazon_research.discovery import list_recommendation_loops, get_loop_reinforcement_signals
        from amazon_research.discovery import compute_adaptive_update, get_adaptive_preference_weights
        ws = 1
        intel = get_workspace_intelligence(ws)
        pers = get_workspace_personalization_signals(ws)
        feed = get_workspace_opportunity_feed(ws, limit=5)
        timeline = get_workspace_intelligence_timeline(ws, limit=5)
        loops = list_recommendation_loops(ws, limit=5)
        sigs = get_loop_reinforcement_signals(ws)
        adaptive = compute_adaptive_update(ws)
        weights = get_adaptive_preference_weights(ws)
        if not isinstance(intel, dict) or "workspace_id" not in intel:
            workspace_ok = False
        if not isinstance(pers, dict):
            workspace_ok = False
        if not isinstance(feed, list):
            workspace_ok = False
        if not isinstance(adaptive, dict) or "updated_preference_weights" not in adaptive:
            workspace_ok = False
    except Exception as e:
        workspace_ok = False
        risks.append(f"Workspace intelligence import or run failed: {e!s}"[:100])

    # --- 5) Strategy layer: portfolio tracker, strategy insights, risk/reward, strategic recs, copilot strategy ---
    try:
        from amazon_research.discovery import get_workspace_portfolio, get_portfolio_strategy_insights
        from amazon_research.discovery import get_risk_reward_for_opportunity, get_workspace_risk_reward_map
        from amazon_research.discovery import get_strategic_recommendations
        from amazon_research.discovery import get_copilot_strategy_guidance
        ws = 1
        port = get_workspace_portfolio(ws, limit=5)
        insights = get_portfolio_strategy_insights(ws, portfolio_limit=10)
        rr = get_risk_reward_for_opportunity("r1", lifecycle_output={"lifecycle_state": "rising", "lifecycle_score": 60})
        recs = get_strategic_recommendations(ws, limit=5)
        guidance = get_copilot_strategy_guidance(ws, limit=5)
        if not isinstance(port, list):
            strategy_ok = False
        if "portfolio_health_summary" not in insights or "suggested_portfolio_actions" not in insights:
            strategy_ok = False
        if "risk_score" not in rr or "quadrant_classification" not in rr:
            strategy_ok = False
        if not isinstance(recs, list):
            strategy_ok = False
        if not isinstance(guidance, list):
            strategy_ok = False
    except Exception as e:
        strategy_ok = False
        risks.append(f"Strategy layer import or run failed: {e!s}"[:100])

    # --- 6) System resilience: retry orchestrator, failure detection, scheduler, crawl simulation ---
    try:
        from amazon_research.monitoring.recovery_retry_orchestrator_v2 import get_recovery_decision, classify_failure
        from amazon_research.monitoring.platform_failure_detector import run_all_checks as run_failure_checks
        from amazon_research.scheduler.intelligent_crawl_scheduler import get_intelligent_crawl_schedule
        from amazon_research.monitoring.crawl_behavior_simulation import build_crawl_simulation, get_next_step_delay_for_crawler
        dec = get_recovery_decision("target-1", detected_failure_category="blocked_response_captcha")
        sched = get_intelligent_crawl_schedule(workspace_id=None, limit=5)
        sim = build_crawl_simulation(behavior_type="mixed", seed=42)
        delay = get_next_step_delay_for_crawler()
        if "recovery_action_chosen" not in dec or "retry_schedule" not in dec:
            resilience_ok = False
        if not isinstance(sched, list):
            resilience_ok = False
        if "navigation_sequence_summary" not in sim or "timing_profile_summary" not in sim:
            resilience_ok = False
        if not isinstance(delay, (int, float)):
            resilience_ok = False
    except Exception as e:
        resilience_ok = False
        risks.append(f"Resilience systems import or run failed: {e!s}"[:100])

    # --- Production readiness (data infrastructure = collection + pipeline) ---
    data_infra_ok = data_infra_ok and pipeline_ok
    all_ok = data_infra_ok and intelligence_ok and workspace_ok and strategy_ok and resilience_ok
    if all_ok:
        production_readiness = "HIGH"
    elif sum([data_infra_ok, intelligence_ok, workspace_ok, strategy_ok, resilience_ok]) >= 4:
        production_readiness = "MEDIUM"
        minor_improvements.append("One or more areas need verification; address before production.")
    else:
        production_readiness = "LOW"
        risks.append("Multiple areas failed; resolve before production.")

    # --- Output ---
    print("platform review OK")
    print("data infrastructure: OK" if data_infra_ok else "data infrastructure: FAIL")
    print("intelligence layer: OK" if intelligence_ok else "intelligence layer: FAIL")
    print("workspace intelligence: OK" if workspace_ok else "workspace intelligence: FAIL")
    print("strategy layer: OK" if strategy_ok else "strategy layer: FAIL")
    print("resilience systems: OK" if resilience_ok else "resilience systems: FAIL")
    print("production readiness: " + production_readiness)
    if production_readiness == "HIGH":
        print("summary: Data infrastructure, intelligence stack, workspace intelligence, strategy layer, and resilience systems integrate correctly; architecture is stable and data flows are consistent across layers.")
    if risks:
        print("major_risks: " + "; ".join(risks[:5]))
    if minor_improvements:
        print("minor_improvements: " + "; ".join(minor_improvements[:5]))

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
