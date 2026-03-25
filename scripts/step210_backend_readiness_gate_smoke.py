#!/usr/bin/env python3
"""
Step 210 smoke test: Backend readiness gate and production safety review.
Validates readiness review generation, subsystem check coverage, warning/failure classification,
payload stability, partial subsystem resilience, operational route compatibility.
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))


def main() -> None:
    from amazon_research.backend_readiness import run_backend_readiness_review, STATUS_READY, STATUS_CAUTION, STATUS_NOT_READY
    from amazon_research.api import get_backend_readiness_response

    gen_ok = True
    coverage_ok = True
    classification_ok = True
    payload_ok = True
    resilience_ok = True
    route_ok = True

    # --- Readiness review generation: run_backend_readiness_review returns full structure
    try:
        review = run_backend_readiness_review()
        if not isinstance(review, dict):
            gen_ok = False
        if "overall_status" not in review or "generated_at" not in review:
            gen_ok = False
        if review.get("overall_status") not in (STATUS_READY, STATUS_CAUTION, STATUS_NOT_READY):
            gen_ok = False
    except Exception as e:
        gen_ok = False
        print(f"readiness review generation error: {e}")

    # --- Subsystem check coverage: passed_checks + warning_checks + failed_checks cover key subsystems
    try:
        review = run_backend_readiness_review()
        passed = review.get("passed_checks") or []
        warnings = review.get("warning_checks") or []
        failed = review.get("failed_checks") or []
        total = len(passed) + len(warnings) + len(failed)
        if total < 5:
            coverage_ok = False
        keys = {c.get("check_key") for c in passed + warnings + failed}
        if "workspace_intelligence_available" not in keys and "persistence_layer_available" not in keys:
            coverage_ok = False
    except Exception as e:
        coverage_ok = False
        print(f"subsystem check coverage error: {e}")

    # --- Warning/failure classification: items have status and severity
    try:
        review = run_backend_readiness_review()
        for item in (review.get("passed_checks") or []) + (review.get("warning_checks") or []) + (review.get("failed_checks") or []):
            if item.get("status") not in ("pass", "warning", "fail"):
                classification_ok = False
            if item.get("severity") not in ("low", "medium", "high", "critical"):
                classification_ok = False
            if "check_key" not in item or "rationale" not in item:
                classification_ok = False
    except Exception as e:
        classification_ok = False
        print(f"warning failure classification error: {e}")

    # --- Payload stability: required top-level keys present
    try:
        review = run_backend_readiness_review()
        for key in ("generated_at", "overall_status", "readiness_score", "passed_checks", "warning_checks", "failed_checks", "subsystem_summary", "top_blockers", "recommended_actions", "notes"):
            if key not in review:
                payload_ok = False
        if not isinstance(review.get("subsystem_summary"), dict):
            payload_ok = False
        if not isinstance(review.get("top_blockers"), list) or not isinstance(review.get("notes"), list):
            payload_ok = False
    except Exception as e:
        payload_ok = False
        print(f"payload stability error: {e}")

    # --- Partial subsystem resilience: review completes even if some checks warn/fail
    try:
        review = run_backend_readiness_review()
        if "overall_status" not in review:
            resilience_ok = False
        if review.get("readiness_score") is None:
            resilience_ok = False
    except Exception as e:
        resilience_ok = False
        print(f"partial subsystem resilience error: {e}")

    # --- Operational route compatibility: API handler returns stable envelope
    try:
        body = get_backend_readiness_response()
        if not isinstance(body, dict):
            route_ok = False
        if "data" not in body and "error" not in body:
            route_ok = False
        if body.get("data") and "overall_status" not in body["data"]:
            route_ok = False
    except Exception as e:
        route_ok = False
        print(f"operational route compatibility error: {e}")

    print("backend readiness gate OK" if all([gen_ok, coverage_ok, classification_ok, payload_ok, resilience_ok, route_ok]) else "backend readiness gate FAIL")
    print("readiness review generation: OK" if gen_ok else "readiness review generation: FAIL")
    print("subsystem check coverage: OK" if coverage_ok else "subsystem check coverage: FAIL")
    print("warning failure classification: OK" if classification_ok else "warning failure classification: FAIL")
    print("payload stability: OK" if payload_ok else "payload stability: FAIL")
    print("partial subsystem resilience: OK" if resilience_ok else "partial subsystem resilience: FAIL")
    print("operational route compatibility: OK" if route_ok else "operational route compatibility: FAIL")
    sys.exit(0 if all([gen_ok, coverage_ok, classification_ok, payload_ok, resilience_ok, route_ok]) else 1)


if __name__ == "__main__":
    main()
