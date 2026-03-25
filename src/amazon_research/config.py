"""
Central configuration from environment variables.
All secrets and tunables live here; no config scattered across modules.

Tuning layer (Step 36): delays, retries, batch sizes, and safety caps are centralized below.
Modules must read these values from get_config(); no hardcoded tuning in other modules.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    """Application config. Load once at startup from env."""

    # Database
    database_url: str

    # Proxy (optional; no credentials = proxy disabled)
    # DataImpulse: host gw.dataimpulse.com, port 823; set PROXY_USERNAME and PROXY_PASSWORD in .env only
    # Rotation v1: optional second endpoint via PROXY_HOST_2, PROXY_PORT_2 (same credentials)
    proxy_host: str = "gw.dataimpulse.com"
    proxy_port: int = 823
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_host_2: Optional[str] = None
    proxy_port_2: Optional[int] = None

    # ---------- Tuning layer: delays, retries, batch sizes, safety caps ----------
    # Delays (seconds)
    request_delay_min_sec: float = 1.0
    request_delay_max_sec: float = 3.0
    discovery_page_wait_sec: float = 3.0  # Wait after loading one Amazon listing page before parsing
    refresh_page_wait_sec: float = 3.0  # Wait after loading one Amazon product page before parsing
    antibot_delay_min_sec: float = 2.0
    antibot_delay_max_sec: float = 5.0
    page_load_timeout_ms: int = 30_000

    # Retries
    max_retries: int = 3
    navigation_retries: int = 3
    navigation_retry_base_sec: float = 1.0
    skip_after_n_failures: int = 3
    skip_duration_hours: float = 1.0

    # Batch sizes and run behavior
    max_discovery_pages: int = 3  # Multi-page discovery cap; no category fan-out
    max_refresh_batch_size: int = 5  # Refresh batch cap; sequential only
    max_refresh_consecutive_failures: int = 2  # Stop batch after this many consecutive failures
    scheduler_refresh_limit: int = 5  # Max ASINs to consider for refresh when run from scheduler
    scheduler_scoring_limit: int = 5  # Max ASINs to score when run from scheduler

    # Safety caps (upper bounds; effective = min(tuning value, cap))
    max_discovery_pages_cap: int = 10
    max_refresh_batch_size_cap: int = 20

    # Related/sponsored discovery (Step 39): optional extraction from product pages; low-volume
    discover_related_sponsored: bool = True
    max_related_per_page: int = 5
    max_sponsored_per_page: int = 5

    # Graph expansion (Step 40): controlled discovery from relationship graph; strict caps
    max_expansion_nodes: int = 5
    max_expansion_candidates: int = 20
    max_expansion_persist: int = 10

    # Multi-market (Step 47): default marketplace; URL built via market module when supported
    default_market: str = "DE"
    amazon_product_base_url: str = "https://www.amazon.com/dp/"  # Fallback when market not in supported list

    # Logging
    log_level: str = "INFO"
    log_format: str = "console"  # "console" or "json"

    # Monitoring (placeholders for Sentry, etc.)
    sentry_dsn: Optional[str] = None
    environment: str = "development"
    # Alerting v1: optional webhook for pipeline failure (disabled if missing)
    alert_webhook_url: Optional[str] = None

    # Internal access control (Step 46): optional API key; when set, internal API requires it
    internal_api_key: Optional[str] = None

    # Rate limiting v1 (Step 57): requests per window per workspace; in-memory sliding window
    rate_limit_api_per_minute: int = 60
    rate_limit_export_per_minute: int = 10

    # Retention (Step 35): delete logs/history older than N days. Core product/metrics/scoring never deleted.
    error_logs_retention_days: int = 90
    bot_runs_retention_days: int = 90
    price_history_retention_days: int = 90
    review_history_retention_days: int = 90

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            database_url=os.environ["DATABASE_URL"],
            proxy_host=os.environ.get("PROXY_HOST", "gw.dataimpulse.com"),
            proxy_port=int(os.environ.get("PROXY_PORT", "823")),
            proxy_username=os.environ.get("PROXY_USERNAME") or None,
            proxy_password=os.environ.get("PROXY_PASSWORD") or None,
            proxy_host_2=os.environ.get("PROXY_HOST_2") or None,
            proxy_port_2=int(px) if (px := os.environ.get("PROXY_PORT_2")) and px.isdigit() else None,
            request_delay_min_sec=float(os.environ.get("REQUEST_DELAY_MIN_SEC", "1.0")),
            request_delay_max_sec=float(os.environ.get("REQUEST_DELAY_MAX_SEC", "3.0")),
            page_load_timeout_ms=int(os.environ.get("PAGE_LOAD_TIMEOUT_MS", "30000")),
            max_retries=int(os.environ.get("MAX_RETRIES", "3")),
            discovery_page_wait_sec=float(os.environ.get("DISCOVERY_PAGE_WAIT_SEC", "3.0")),
            max_discovery_pages=int(os.environ.get("MAX_DISCOVERY_PAGES", "3")),
            refresh_page_wait_sec=float(os.environ.get("REFRESH_PAGE_WAIT_SEC", "3.0")),
            max_refresh_batch_size=int(os.environ.get("MAX_REFRESH_BATCH_SIZE", "5")),
            max_refresh_consecutive_failures=int(os.environ.get("MAX_REFRESH_CONSECUTIVE_FAILURES", "2")),
            scheduler_refresh_limit=max(1, int(os.environ.get("SCHEDULER_REFRESH_LIMIT", "5"))),
            scheduler_scoring_limit=max(1, int(os.environ.get("SCHEDULER_SCORING_LIMIT", "5"))),
            max_discovery_pages_cap=max(1, int(os.environ.get("MAX_DISCOVERY_PAGES_CAP", "10"))),
            max_refresh_batch_size_cap=max(1, int(os.environ.get("MAX_REFRESH_BATCH_SIZE_CAP", "20"))),
            discover_related_sponsored=os.environ.get("DISCOVER_RELATED_SPONSORED", "true").strip().lower() in ("1", "true", "yes"),
            max_related_per_page=max(0, min(20, int(os.environ.get("MAX_RELATED_PER_PAGE", "5")))),
            max_sponsored_per_page=max(0, min(20, int(os.environ.get("MAX_SPONSORED_PER_PAGE", "5")))),
            max_expansion_nodes=max(1, min(20, int(os.environ.get("MAX_EXPANSION_NODES", "5")))),
            max_expansion_candidates=max(1, min(100, int(os.environ.get("MAX_EXPANSION_CANDIDATES", "20")))),
            max_expansion_persist=max(0, min(50, int(os.environ.get("MAX_EXPANSION_PERSIST", "10")))),
            default_market=(os.environ.get("DEFAULT_MARKET", "DE") or "DE").strip().upper()[:10],
            amazon_product_base_url=os.environ.get("AMAZON_PRODUCT_BASE_URL", "https://www.amazon.de/dp/").rstrip("/") + "/",
            antibot_delay_min_sec=float(os.environ.get("ANTIBOT_DELAY_MIN_SEC", "2.0")),
            antibot_delay_max_sec=float(os.environ.get("ANTIBOT_DELAY_MAX_SEC", "5.0")),
            navigation_retries=int(os.environ.get("NAVIGATION_RETRIES", "3")),
            navigation_retry_base_sec=float(os.environ.get("NAVIGATION_RETRY_BASE_SEC", "1.0")),
            skip_after_n_failures=int(os.environ.get("SKIP_AFTER_N_FAILURES", "3")),
            skip_duration_hours=float(os.environ.get("SKIP_DURATION_HOURS", "1.0")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            log_format=os.environ.get("LOG_FORMAT", "console"),
            sentry_dsn=os.environ.get("SENTRY_DSN") or None,
            environment=os.environ.get("ENVIRONMENT", "development"),
            alert_webhook_url=os.environ.get("ALERT_WEBHOOK_URL") or None,
            internal_api_key=os.environ.get("INTERNAL_API_KEY") or None,
            rate_limit_api_per_minute=max(1, int(os.environ.get("RATE_LIMIT_API_PER_MINUTE", "60"))),
            rate_limit_export_per_minute=max(1, int(os.environ.get("RATE_LIMIT_EXPORT_PER_MINUTE", "10"))),
            error_logs_retention_days=max(1, int(os.environ.get("ERROR_LOGS_RETENTION_DAYS", "90"))),
            bot_runs_retention_days=max(1, int(os.environ.get("BOT_RUNS_RETENTION_DAYS", "90"))),
            price_history_retention_days=max(1, int(os.environ.get("PRICE_HISTORY_RETENTION_DAYS", "90"))),
            review_history_retention_days=max(1, int(os.environ.get("REVIEW_HISTORY_RETENTION_DAYS", "90"))),
        )


def get_config() -> Config:
    """Return config loaded from env. Use this everywhere instead of reading os.environ."""
    return Config.from_env()
