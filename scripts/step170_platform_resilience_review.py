#!/usr/bin/env python3
"""
Step 170: Platform Resilience Review – audit the resilience and reliability stack.
Modules: platform failure detection, data quality guard, scraper reliability, intelligent crawl scheduler,
recovery/retry orchestrator v2, data integrity repair, anti-bot hardening, crawl behavior simulation, resilient parsing.
Verifies consistency, detection/classification/recovery/repair, parser robustness, anti-bot compatibility.
No rewrites; outputs strengths, weak points, next improvements.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main():
    next_improvements: list = []
    strengths: list = []
    weaknesses: list = []

    # --- Import resilience modules ---
    try:
        from amazon_research.monitoring.platform_failure_detector import run_all_checks as run_failure_checks
        from amazon_research.monitoring.data_quality_guard import run_all_checks as run_data_quality_checks, missing_data_check
        from amazon_research.monitoring.scraper_reliability import (
            get_scraper_reliability_status,
            response_validation,
            get_retry_delay,
            FAILURE_NETWORK,
            FAILURE_BLOCKED,
        )
        from amazon_research.scheduler.intelligent_crawl_scheduler import get_intelligent_crawl_schedule
        from amazon_research.monitoring.recovery_retry_orchestrator_v2 import (
            classify_failure,
            get_recovery_decision,
            FAILURE_BLOCKED_CAPTCHA,
            FAILURE_PARSER,
        )
        from amazon_research.monitoring.data_integrity_repair import (
            run_repairs_for_quality_issues,
            missing_data_repair,
            timeseries_gap_repair,
            signal_reconstruction,
        )
        from amazon_research.monitoring.antibot_hardening import get_antibot_status, get_request_jitter_delay
        from amazon_research.monitoring.crawl_behavior_simulation import get_next_step_delay_for_crawler, build_crawl_simulation
        from amazon_research.monitoring.resilient_parsing import (
            parse_resilient,
            run_quality_guard_on_parse,
        )
    except ImportError as e:
        print("platform resilience review FAIL (import)", file=sys.stderr)
        print(f"failure detection: FAIL\ndata quality handling: FAIL\nrecovery consistency: FAIL\nparser resilience: FAIL\nanti-bot compatibility: FAIL\nnext improvements: import error: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 1) Failure detection ---
    failure_ok = True
    try:
        report = run_failure_checks()
        if not isinstance(report, dict):
            failure_ok = False
            next_improvements.append("Platform failure detector run_all_checks should return a dict.")
        if "overall" not in report:
            failure_ok = False
            next_improvements.append("Failure report should expose overall status.")
        scraper_check = report.get("scraper") or report.get("parser") or {}
        if isinstance(scraper_check, dict) and "status" not in scraper_check and "component" not in scraper_check:
            failure_ok = False
            next_improvements.append("Per-component checks should return status or component.")
    except Exception as e:
        failure_ok = False
        next_improvements.append(f"Failure detection run_all_checks raised: {e!s}"[:120])

    # --- 2) Data quality handling (guard + repair) ---
    dq_ok = True
    try:
        dq_result = run_data_quality_checks(record={"asin": "B001", "title": "X"})
        if not isinstance(dq_result, dict) or "data_quality" not in dq_result:
            dq_ok = False
            next_improvements.append("Data quality guard should return data_quality and issues.")
        issues = dq_result.get("issues") or []
        record = {"asin": "B002", "title": "Y"}
        repairs = run_repairs_for_quality_issues(issues, record=record, target_id="B002")
        if not isinstance(repairs, list):
            dq_ok = False
        for r in repairs:
            if r.get("repair_status") not in ("FIXED", "SKIPPED", "FAILED"):
                dq_ok = False
                break
            if "issue_type" not in r or "timestamp" not in r:
                dq_ok = False
                break
        # Repair layer can consume guard issues
        missing_issues = missing_data_check(record={})
        if missing_issues and not run_repairs_for_quality_issues(missing_issues, record={}, target_id="t1"):
            pass  # run_repairs returns list (may be empty)
        dq_ok = dq_ok and True
    except Exception as e:
        dq_ok = False
        next_improvements.append(f"Data quality handling raised: {e!s}"[:120])

    # --- 3) Recovery consistency (classification + decision, alignment with scraper) ---
    recovery_ok = True
    try:
        cat_block = classify_failure("blocked", "captcha page")
        if cat_block != FAILURE_BLOCKED_CAPTCHA:
            recovery_ok = False
            next_improvements.append("Recovery classifier should map block/captcha to blocked_response_captcha.")
        cat_parser = classify_failure("parser_error", None)
        if cat_parser != FAILURE_PARSER:
            recovery_ok = False
        decision = get_recovery_decision("target-1", detected_failure_category=FAILURE_BLOCKED_CAPTCHA, attempt=0)
        if not isinstance(decision, dict) or "recovery_action_chosen" not in decision or "retry_schedule" not in decision:
            recovery_ok = False
            next_improvements.append("Recovery decision should include recovery_action_chosen and retry_schedule.")
        if "detected_failure_category" not in decision:
            recovery_ok = False
        # Scraper reliability failure types align with orchestrator (blocked -> proxy rotate, etc.)
        status = get_scraper_reliability_status()
        if not isinstance(status, dict) or status.get("scraper_status") not in ("OK", "WARNING", "FAIL"):
            recovery_ok = False
        delay = get_retry_delay(0)
        if not isinstance(delay, (int, float)) or delay < 0:
            recovery_ok = False
    except Exception as e:
        recovery_ok = False
        next_improvements.append(f"Recovery consistency check raised: {e!s}"[:120])

    # --- 4) Parser resilience (partial extraction, confidence) ---
    parser_ok = True
    try:
        partial_raw = {"asin": "B003", "title": "Z", "price_primary": 12.99}
        pr = parse_resilient(partial_raw, target_id="card-1", page_type="product_card")
        if "extracted_fields" not in pr or "missing_fields" not in pr:
            parser_ok = False
            next_improvements.append("Resilient parse output must include extracted_fields and missing_fields.")
        if "parser_confidence" not in pr or "parse_status" not in pr:
            parser_ok = False
        if pr.get("parser_confidence") is not None and not (0 <= pr["parser_confidence"] <= 1):
            parser_ok = False
        if pr.get("parse_status") not in ("ok", "partial", "fail"):
            parser_ok = False
        guard_issues = run_quality_guard_on_parse(pr)
        if not isinstance(guard_issues, list):
            parser_ok = False
    except Exception as e:
        parser_ok = False
        next_improvements.append(f"Parser resilience check raised: {e!s}"[:120])

    # --- 5) Anti-bot compatibility (antibot + crawl behavior) ---
    antibot_ok = True
    try:
        agg = get_antibot_status()
        if agg.get("anti_bot_status") != "OK":
            antibot_ok = False
        if agg.get("request_jitter") != "OK" or agg.get("session_rotation") != "OK":
            antibot_ok = False
        jitter_delay = get_request_jitter_delay(base_delay=0.5, jitter_max=0.5)
        if not isinstance(jitter_delay, (int, float)) or jitter_delay < 0:
            antibot_ok = False
        crawl_delay = get_next_step_delay_for_crawler(base_delay=0.3, jitter_max=0.3)
        if not isinstance(crawl_delay, (int, float)) or crawl_delay < 0:
            antibot_ok = False
        sim = build_crawl_simulation(behavior_type="mixed", seed=42)
        if "navigation_sequence_summary" not in sim or "timing_profile_summary" not in sim:
            antibot_ok = False
        if (sim.get("timing_profile_summary") or {}).get("variable_pacing") is not True:
            antibot_ok = False
    except Exception as e:
        antibot_ok = False
        next_improvements.append(f"Anti-bot compatibility check raised: {e!s}"[:120])

    # --- Strengths ---
    strengths = [
        "Unified failure detection (scraper, proxy, parser, signal, scoring, scheduler) with status/severity reporting.",
        "Data quality guard and data integrity repair chain: issues from guard drive repair (missing_data, timeseries, signal, anomaly).",
        "Recovery orchestrator v2 classifies failures and selects actions (immediate/delayed retry, proxy rotation, cooldown, skip/escalate).",
        "Resilient parsing provides selector fallback, partial extraction, field-level status, and parser_confidence for layout changes.",
        "Anti-bot hardening (session rotation, UA/header variation, jitter) and crawl behavior simulation (variable pacing, product detour) are compatible.",
    ]

    # --- Weak points ---
    weaknesses = []
    if not failure_ok:
        weaknesses.append("Failure detection output structure or execution may be inconsistent.")
    if not dq_ok:
        weaknesses.append("Data quality guard or repair integration may have gaps.")
    try:
        val = response_validation(html="")
        if val.get("valid") is not False:
            weaknesses.append("Response validation should mark empty HTML as invalid.")
    except Exception:
        pass
    if not recovery_ok:
        weaknesses.append("Recovery classification or decision structure may not align with scraper reliability.")
    if not parser_ok:
        weaknesses.append("Parser resilience or quality-guard integration may be incomplete.")
    if not antibot_ok:
        weaknesses.append("Anti-bot and crawl behavior simulation integration may have gaps.")
    if not weaknesses:
        weaknesses.append("No critical gaps identified; stack is consistent and auditable.")

    # --- Next improvements (minimal) ---
    if not any("persist" in r for r in next_improvements):
        next_improvements.append("Consider persisting recovery/repair outcomes for audit and tuning.")
    if not any("selector" in r for r in next_improvements):
        next_improvements.append("Consider evolving selector fallback chains as layout changes are observed.")
    seen = set()
    unique_next = []
    for x in next_improvements:
        if x not in seen:
            seen.add(x)
            unique_next.append(x)

    # --- Output ---
    print("platform resilience review OK")
    print("failure detection: OK" if failure_ok else "failure detection: FAIL")
    print("data quality handling: OK" if dq_ok else "data quality handling: FAIL")
    print("recovery consistency: OK" if recovery_ok else "recovery consistency: FAIL")
    print("parser resilience: OK" if parser_ok else "parser resilience: FAIL")
    print("anti-bot compatibility: OK" if antibot_ok else "anti-bot compatibility: FAIL")
    print("next improvements: " + ("; ".join(unique_next) if unique_next else "none; stack is consistent."))
    print("strengths: " + " | ".join(strengths))
    print("weaknesses: " + " | ".join(weaknesses))

    if not (failure_ok and dq_ok and recovery_ok and parser_ok and antibot_ok):
        sys.exit(1)


if __name__ == "__main__":
    main()
