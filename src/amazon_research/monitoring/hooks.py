"""
Monitoring hooks – error capture (Sentry-ready), health check, alerting. Ready for Grafana / Uptime Kuma.
Step 34: optional pipeline failure webhook; disabled when ALERT_WEBHOOK_URL missing.
"""
import json
import urllib.request
from typing import Any, Dict, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring")

_sentry_initialized = False


def init_sentry() -> bool:
    """
    Optional Sentry init from SENTRY_DSN. Call once at startup (e.g. from main).
    Returns True if Sentry was initialized, False if disabled or init failed. Never logs or prints DSN.
    """
    global _sentry_initialized
    try:
        from amazon_research.config import get_config
        cfg = get_config()
        dsn = getattr(cfg, "sentry_dsn", None) or None
        if not dsn or not dsn.strip():
            return False
        import sentry_sdk
        sentry_sdk.init(
            dsn=dsn.strip(),
            environment=getattr(cfg, "environment", "development"),
            traces_sample_rate=0.0,
        )
        _sentry_initialized = True
        logger.info("sentry initialized", extra={"environment": getattr(cfg, "environment", "development")})
        return True
    except Exception as e:
        logger.debug("sentry init skipped: %s", e)
        return False


def sentry_status() -> str:
    """Return 'enabled' or 'disabled'. Never leaks DSN or secrets."""
    return "enabled" if _sentry_initialized else "disabled"


def capture_exception(error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Log and optionally send to Sentry. When Sentry is initialized (SENTRY_DSN set), captures exception.
    Call this from bot/scheduler try/except. Never logs or prints DSN.
    """
    ctx = context or {}
    logger.exception("captured exception", extra={"context": ctx})
    if not _sentry_initialized:
        return
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(error)
    except Exception as e:
        logger.debug("sentry capture skipped: %s", e)


def send_pipeline_failure_alert(result: Dict[str, Any]) -> None:
    """
    Optional webhook alert on pipeline failure. If ALERT_WEBHOOK_URL is set, POST compact JSON.
    Payload: event, stopped_at, error, stages_completed. No secrets. No-op when URL missing.
    """
    try:
        from amazon_research.config import get_config
        cfg = get_config()
        url = getattr(cfg, "alert_webhook_url", None) or None
        if not url or not str(url).strip():
            return
        payload = {
            "event": "pipeline_failure",
            "stopped_at": result.get("stopped_at"),
            "error": (str(result.get("error") or ""))[:500],
            "stages_completed": result.get("stages_completed") or [],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url.strip(),
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        logger.warning("alert webhook failed: %s", e)


def _check_db() -> str:
    """Database connectivity. Returns 'ok' or error message."""
    try:
        from amazon_research.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        return "ok"
    except Exception as e:
        return str(e)


def _check_browser() -> str:
    """Browser readiness (Playwright Chromium start/close). Returns 'ok' or error message."""
    try:
        from amazon_research.browser import BrowserSession
        session = BrowserSession(headless=True)
        session.start()
        session.close()
        return "ok"
    except Exception as e:
        return str(e)


def _check_proxy() -> str:
    """Proxy readiness summary. Returns 'enabled' or 'disabled' (no credentials in output)."""
    try:
        from amazon_research.proxy import ProxyManager
        pm = ProxyManager.from_config()
        return "enabled" if pm.get_playwright_proxy() else "disabled"
    except Exception as e:
        return str(e)


def _check_scheduler() -> str:
    """Scheduler readiness (pipeline stages registered). Returns 'ok' or error message."""
    try:
        from amazon_research.scheduler import get_runner, PIPELINE_ORDER
        runner = get_runner()
        for name in PIPELINE_ORDER:
            if name not in getattr(runner, "_by_name", {}):
                return f"missing stage: {name}"
        return "ok"
    except Exception as e:
        return str(e)


def health_check() -> Dict[str, Any]:
    """
    Return health status for Uptime Kuma / load balancer.
    Includes: db, browser readiness, proxy summary (enabled/disabled), scheduler readiness.
    """
    out: Dict[str, Any] = {"status": "ok", "service": "amazon_research"}
    out["db"] = _check_db()
    out["browser"] = _check_browser()
    out["proxy"] = _check_proxy()
    out["scheduler"] = _check_scheduler()
    if out["db"] != "ok" or out["browser"] != "ok" or out["scheduler"] != "ok":
        out["status"] = "degraded"
    return out
