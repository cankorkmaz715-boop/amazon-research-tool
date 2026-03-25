"""
Step 163: Scraper reliability layer – retry, proxy rotation, response validation, throttling, failure tracking, recovery.
Wrapper layer only; does not alter discovery engine. Ensures scraping continues smoothly despite failures, blocks, unstable responses.
"""
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.scraper_reliability")

STATUS_OK = "OK"
STATUS_WARNING = "WARNING"
STATUS_FAIL = "FAIL"

# Retry: exponential backoff delays (seconds) for attempt 1, 2, 3, ...
RETRY_DELAYS = [2, 5, 10, 20, 40]

# Failure categories for tracker
FAILURE_NETWORK = "network_error"
FAILURE_PROXY = "proxy_error"
FAILURE_PARSER = "parser_error"
FAILURE_BLOCKED = "blocked_page"

# In-memory state (per process)
_throttle_counts: Dict[str, deque] = {}  # domain -> deque of timestamps
_throttle_max_per_minute = 30
_throttle_cooldown_seconds = 1.0
_last_request_time: Dict[str, float] = {}
_failures: List[Dict[str, Any]] = []
_recovery_queue: List[Dict[str, Any]] = []


# --- 1) Retry controller ---
def get_retry_delay(attempt: int) -> float:
    """Return delay in seconds for given attempt (0-based). Exponential backoff: attempt 0 -> 2s, 1 -> 5s, 2 -> 10s, ..."""
    idx = min(max(0, attempt), len(RETRY_DELAYS) - 1)
    return float(RETRY_DELAYS[idx])


def retry_controller(
    fn: Callable[[], Any],
    max_attempts: int = 3,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Any:
    """Execute fn with retries and exponential backoff. Does not catch; caller can use for wrapper. On last attempt re-raises."""
    last_exc: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < max_attempts - 1:
                delay = get_retry_delay(attempt)
                if on_retry:
                    on_retry(attempt, e)
                time.sleep(delay)
            else:
                raise
    if last_exc is not None:
        raise last_exc
    return None


# --- 2) Proxy rotation guard ---
def should_rotate_proxy(failure_type: str, response_indicators_block: bool = False) -> bool:
    """Return True when proxy should be rotated: connection fail, timeout, or block indicated."""
    t = (failure_type or "").strip().lower()
    if t in ("connection_fail", "connection_failed", "timeout", "block", "blocked"):
        return True
    if response_indicators_block:
        return True
    if t in (FAILURE_PROXY, FAILURE_BLOCKED):
        return True
    return False


def proxy_rotation_guard(failure_type: str, response_body: Optional[str] = None) -> Dict[str, Any]:
    """Recommend whether to rotate proxy and return status. Does not perform rotation."""
    block_indicators = _is_block_or_captcha(response_body or "")
    rotate = should_rotate_proxy(failure_type, response_indicators_block=block_indicators)
    return {"rotate_recommended": rotate, "reason": failure_type or "unknown", "status": STATUS_OK}


# --- 3) Response validation ---
def _is_block_or_captcha(html: str) -> bool:
    """Simple heuristic: captcha or bot detection page."""
    if not html or len(html) < 20:
        return False
    lower = html.lower()
    if "captcha" in lower or "unusual traffic" in lower or "robot" in lower:
        return True
    if "blocked" in lower and "access" in lower:
        return True
    if "automated access" in lower or "bot detection" in lower:
        return True
    return False


def response_validation(html: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
    """Check if page response is valid. Detect empty HTML, captcha, bot detection. Returns valid (bool), reason (str)."""
    if html is None:
        return {"valid": False, "reason": "empty_response", "status": STATUS_FAIL}
    if not isinstance(html, str):
        return {"valid": False, "reason": "invalid_type", "status": STATUS_FAIL}
    stripped = html.strip()
    if len(stripped) < 50:
        return {"valid": False, "reason": "empty_or_tiny_html", "status": STATUS_FAIL}
    if _is_block_or_captcha(stripped):
        return {"valid": False, "reason": "captcha_or_block_page", "status": STATUS_FAIL}
    return {"valid": True, "reason": "ok", "status": STATUS_OK}


# --- 4) Request throttling ---
def request_throttling(domain: str, max_per_minute: int = 30, cooldown_seconds: float = 1.0) -> Dict[str, Any]:
    """Check if a request to domain is allowed under throttling. Optionally record after. Returns can_send (bool), wait_seconds (float)."""
    now = time.time()
    key = (domain or "").strip() or "default"
    if key not in _throttle_counts:
        _throttle_counts[key] = deque(maxlen=max_per_minute * 2)
    q = _throttle_counts[key]
    # Drop timestamps older than 1 minute
    while q and now - q[0] > 60:
        q.popleft()
    last = _last_request_time.get(key, 0)
    wait = max(0.0, cooldown_seconds - (now - last))
    can_send = len(q) < max_per_minute and wait <= 0
    return {"can_send": can_send, "wait_seconds": wait if not can_send else 0, "requests_last_minute": len(q), "status": STATUS_OK}


def record_request(domain: str) -> None:
    """Record that a request was sent to domain (for throttling)."""
    key = (domain or "").strip() or "default"
    _last_request_time[key] = time.time()
    if key not in _throttle_counts:
        _throttle_counts[key] = deque(maxlen=_throttle_max_per_minute * 2)
    _throttle_counts[key].append(time.time())


# --- 5) Scrape failure tracker ---
def scrape_failure_tracker_record(category: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Record a scraping failure. Category: network_error, proxy_error, parser_error, blocked_page."""
    c = (category or "").strip().lower()
    if c not in (FAILURE_NETWORK, FAILURE_PROXY, FAILURE_PARSER, FAILURE_BLOCKED):
        c = FAILURE_NETWORK
    _failures.append({
        "category": c,
        "details": dict(details or {}),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    # Keep last N to avoid unbounded growth
    while len(_failures) > 500:
        _failures.pop(0)


def scrape_failure_tracker_summary(limit: int = 100) -> Dict[str, Any]:
    """Return failure counts by category and recent list. Status OK if tracker operable."""
    recent = _failures[-limit:]
    by_cat: Dict[str, int] = {}
    for f in _failures:
        cat = f.get("category") or "unknown"
        by_cat[cat] = by_cat.get(cat, 0) + 1
    return {"by_category": by_cat, "recent_count": len(recent), "total": len(_failures), "status": STATUS_OK}


# --- 6) Recovery scheduler ---
def recovery_scheduler_add(task: Dict[str, Any]) -> str:
    """Queue a failed scrape task for retry later. Returns task_id."""
    task_id = str(uuid.uuid4())[:12]
    _recovery_queue.append({"task_id": task_id, "task": dict(task), "added_at": datetime.now(timezone.utc).isoformat()})
    while len(_recovery_queue) > 1000:
        _recovery_queue.pop(0)
    return task_id


def recovery_scheduler_pending(limit: int = 50) -> List[Dict[str, Any]]:
    """Return list of pending retry tasks."""
    return list(_recovery_queue[-limit:])


def recovery_scheduler_mark_retried(task_id: str) -> bool:
    """Remove task from pending (e.g. after retry attempted). Returns True if found."""
    for i, t in enumerate(_recovery_queue):
        if t.get("task_id") == task_id:
            _recovery_queue.pop(i)
            return True
    return False


# --- Status aggregate ---
def get_scraper_reliability_status() -> Dict[str, Any]:
    """Return aggregate status: scraper_status, retry_system, proxy_rotation, response_validation, throttling, failure_tracking."""
    return {
        "scraper_status": STATUS_OK,
        "retry_system": STATUS_OK,
        "proxy_rotation": STATUS_OK,
        "response_validation": STATUS_OK,
        "throttling": STATUS_OK,
        "failure_tracking": STATUS_OK,
    }
