"""
Step 161: Platform failure detection layer – detect scraper, proxy, parser, signal, scoring, and scheduler failures.
Lightweight: monitor pipeline execution results, detect abnormal states, produce failure reports.
Does not interrupt platform execution; only detect and report.
"""
from typing import Any, Dict

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.platform_failure_detector")

STATUS_OK = "OK"
STATUS_WARNING = "WARNING"
STATUS_FAIL = "FAIL"
SEVERITY_LOW = "low"
SEVERITY_MEDIUM = "medium"
SEVERITY_HIGH = "high"


def _report(status: str, component: str, reason: str, severity: str) -> Dict[str, Any]:
    """Produce standard failure report format."""
    return {
        "status": status,
        "component": component,
        "reason": reason,
        "severity": severity,
    }


def scraper_health_check() -> Dict[str, Any]:
    """
    Check scraper/crawler health from operational health or runtime metrics.
    Returns standard report: status (OK|WARNING|FAIL), component, reason, severity.
    """
    try:
        from amazon_research.monitoring import get_operational_health
        health = get_operational_health()
        components = health.get("components") or {}
        crawler = components.get("crawler") or {}
        status = (crawler.get("status") or "healthy").lower()
        message = crawler.get("message") or "no crawler data"
        if status == "critical":
            return _report(STATUS_FAIL, "scraper", message, SEVERITY_HIGH)
        if status == "warning":
            return _report(STATUS_WARNING, "scraper", message, SEVERITY_MEDIUM)
        return _report(STATUS_OK, "scraper", message or "scraper ok", SEVERITY_LOW)
    except Exception as e:
        logger.debug("scraper_health_check: %s", e)
        return _report(STATUS_WARNING, "scraper", f"check unavailable: {e!s}"[:200], SEVERITY_MEDIUM)


def proxy_connection_check() -> Dict[str, Any]:
    """
    Check proxy configuration and connectivity readiness.
    Returns standard report. Does not open live connections; only validates config.
    """
    try:
        from amazon_research.proxy.manager import ProxyManager
        pm = ProxyManager.from_config()
        pool = getattr(pm, "_pool", [])
        enabled = getattr(pm, "_enabled", False)
        if not pool and not enabled:
            return _report(STATUS_WARNING, "proxy", "proxy not configured or disabled", SEVERITY_MEDIUM)
        if not pool:
            return _report(STATUS_WARNING, "proxy", "proxy pool empty", SEVERITY_MEDIUM)
        return _report(STATUS_OK, "proxy", f"proxy configured (pool size {len(pool)})", SEVERITY_LOW)
    except Exception as e:
        logger.debug("proxy_connection_check: %s", e)
        return _report(STATUS_WARNING, "proxy", f"check unavailable: {e!s}"[:200], SEVERITY_MEDIUM)


def parser_integrity_check() -> Dict[str, Any]:
    """
    Check that parsers are loadable and structurally valid.
    Does not run full parse; only verifies module integrity.
    """
    try:
        from amazon_research.parsers import listing, product
        if listing is None and product is None:
            return _report(STATUS_WARNING, "parser", "parser modules not found", SEVERITY_MEDIUM)
        return _report(STATUS_OK, "parser", "parser modules loadable", SEVERITY_LOW)
    except Exception as e:
        logger.debug("parser_integrity_check: %s", e)
        return _report(STATUS_FAIL, "parser", f"parser load failed: {e!s}"[:200], SEVERITY_HIGH)


def signal_integrity_check(sample_size: int = 20) -> Dict[str, Any]:
    """
    Check for signal gaps: missing demand, competition, or trend signals in opportunity data.
    Returns FAIL if a majority of sampled records lack expected signal fields.
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=sample_size)
        if not rows:
            return _report(STATUS_OK, "signal", "no opportunity data to check", SEVERITY_LOW)
        missing = 0
        for r in rows:
            ctx = r.get("context") or {}
            if ctx.get("demand_score") is None and ctx.get("competition_score") is None:
                missing += 1
        ratio = missing / len(rows)
        if ratio >= 0.8:
            return _report(STATUS_FAIL, "signal", f"signal gap: {missing}/{len(rows)} records missing demand/competition", SEVERITY_HIGH)
        if ratio >= 0.5:
            return _report(STATUS_WARNING, "signal", f"partial signal gap: {missing}/{len(rows)} records", SEVERITY_MEDIUM)
        return _report(STATUS_OK, "signal", f"signals present in sampled {len(rows)} records", SEVERITY_LOW)
    except Exception as e:
        logger.debug("signal_integrity_check: %s", e)
        return _report(STATUS_WARNING, "signal", f"check unavailable: {e!s}"[:200], SEVERITY_MEDIUM)


def scoring_sanity_check(sample_size: int = 20) -> Dict[str, Any]:
    """
    Check for scoring anomalies: scores outside expected range (e.g. 0–100).
    Returns WARNING/FAIL if many scores are missing or out of range.
    """
    try:
        from amazon_research.db import list_opportunity_memory
        rows = list_opportunity_memory(limit=sample_size)
        if not rows:
            return _report(STATUS_OK, "scoring", "no opportunity data to check", SEVERITY_LOW)
        out_of_range = 0
        missing = 0
        for r in rows:
            score = r.get("latest_opportunity_score")
            if score is None:
                missing += 1
                continue
            try:
                s = float(score)
                if s < 0 or s > 100:
                    out_of_range += 1
            except (TypeError, ValueError):
                out_of_range += 1
        total_anomalous = missing + out_of_range
        if total_anomalous >= len(rows) * 0.8:
            return _report(STATUS_FAIL, "scoring", f"scoring anomaly: {total_anomalous}/{len(rows)} missing or out of range", SEVERITY_HIGH)
        if total_anomalous >= len(rows) * 0.5:
            return _report(STATUS_WARNING, "scoring", f"scoring anomaly: {total_anomalous}/{len(rows)} records", SEVERITY_MEDIUM)
        return _report(STATUS_OK, "scoring", f"scores sane in sampled {len(rows)} records", SEVERITY_LOW)
    except Exception as e:
        logger.debug("scoring_sanity_check: %s", e)
        return _report(STATUS_WARNING, "scoring", f"check unavailable: {e!s}"[:200], SEVERITY_MEDIUM)


def scheduler_job_check(limit: int = 50) -> Dict[str, Any]:
    """
    Check scheduler/job execution: recent failed jobs or worker health.
    Returns standard report. Does not modify queue or jobs.
    """
    try:
        from amazon_research.monitoring import get_operational_health
        health = get_operational_health()
        components = health.get("components") or {}
        worker = components.get("worker") or {}
        scheduler = components.get("scheduler") or {}
        status_w = (worker.get("status") or "healthy").lower()
        status_s = (scheduler.get("status") or "healthy").lower()
        if status_w == "critical" or status_s == "critical":
            return _report(STATUS_FAIL, "scheduler", worker.get("message") or scheduler.get("message") or "scheduler/worker critical", SEVERITY_HIGH)
        if status_w == "warning" or status_s == "warning":
            return _report(STATUS_WARNING, "scheduler", worker.get("message") or scheduler.get("message") or "scheduler/worker warning", SEVERITY_MEDIUM)
        try:
            from amazon_research.db import list_jobs
            jobs = list_jobs(limit=limit, status="failed")
            if jobs and len(jobs) >= 10:
                return _report(STATUS_WARNING, "scheduler", f"{len(jobs)} recent failed jobs", SEVERITY_MEDIUM)
        except Exception:
            pass
        return _report(STATUS_OK, "scheduler", (scheduler.get("message") or worker.get("message") or "scheduler ok"), SEVERITY_LOW)
    except Exception as e:
        logger.debug("scheduler_job_check: %s", e)
        return _report(STATUS_WARNING, "scheduler", f"check unavailable: {e!s}"[:200], SEVERITY_MEDIUM)


def run_all_checks(
    signal_sample_size: int = 20,
    job_limit: int = 50,
) -> Dict[str, Any]:
    """
    Run all failure detection checks. Returns dict with keys per component and overall status.
    Does not interrupt execution; only detect and report.
    """
    results = {
        "scraper": scraper_health_check(),
        "proxy": proxy_connection_check(),
        "parser": parser_integrity_check(),
        "signal": signal_integrity_check(sample_size=signal_sample_size),
        "scoring": scoring_sanity_check(sample_size=signal_sample_size),
        "scheduler": scheduler_job_check(limit=job_limit),
    }
    statuses = [r.get("status") for r in results.values()]
    if STATUS_FAIL in statuses:
        results["overall"] = STATUS_FAIL
    elif STATUS_WARNING in statuses:
        results["overall"] = STATUS_WARNING
    else:
        results["overall"] = STATUS_OK
    return results
