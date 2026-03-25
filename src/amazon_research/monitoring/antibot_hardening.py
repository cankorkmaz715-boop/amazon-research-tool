"""
Step 167: Anti-bot hardening layer – strengthen scraping against bot detection.
Session rotation, user-agent randomization, header variation, request jitter,
navigation pattern simulation, captcha/block detection and classification.
Does not modify crawler discovery logic; only hardens request behavior.
"""
import random
import time
import uuid
from typing import Any, Dict, List, Optional

from amazon_research.logging_config import get_logger

logger = get_logger("monitoring.antibot_hardening")

STATUS_OK = "OK"

# --- 1) Session rotation manager ---
_session_id: Optional[str] = None
_session_created_at: float = 0.0
_session_request_count: int = 0
ROTATE_AFTER_REQUESTS = 50
ROTATE_AFTER_SECONDS = 1800.0  # 30 min


def _now() -> float:
    return time.time()


def get_current_session_id() -> str:
    """Return current browser/session identifier. Creates one if none exists."""
    global _session_id, _session_created_at, _session_request_count
    if _session_id is None:
        _session_id = str(uuid.uuid4())[:16]
        _session_created_at = _now()
        _session_request_count = 0
    return _session_id


def should_rotate_session() -> bool:
    """Return True if session should be rotated (by request count or age)."""
    get_current_session_id()
    if _session_request_count >= ROTATE_AFTER_REQUESTS:
        return True
    if _now() - _session_created_at >= ROTATE_AFTER_SECONDS:
        return True
    return False


def rotate_session() -> str:
    """Rotate to a new session; return new session id."""
    global _session_id, _session_created_at, _session_request_count
    _session_id = str(uuid.uuid4())[:16]
    _session_created_at = _now()
    _session_request_count = 0
    return _session_id


def record_session_request() -> None:
    """Record that a request was made with the current session (for rotation logic)."""
    global _session_request_count
    get_current_session_id()
    _session_request_count += 1


def session_rotation_manager_status() -> Dict[str, Any]:
    """Return status of session rotation (current id, should_rotate, etc.)."""
    sid = get_current_session_id()
    return {
        "current_session_id": sid,
        "should_rotate": should_rotate_session(),
        "request_count": _session_request_count,
        "status": STATUS_OK,
    }


# --- 2) User-Agent randomizer ---
USER_AGENT_POOL: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_random_user_agent() -> str:
    """Return a random user-agent from the safe pool."""
    return random.choice(USER_AGENT_POOL)


def user_agent_randomizer_status() -> Dict[str, Any]:
    """Return status (pool size, sample)."""
    return {
        "pool_size": len(USER_AGENT_POOL),
        "sample_ua": get_random_user_agent()[:60] + "...",
        "status": STATUS_OK,
    }


# --- 3) Header variation ---
ACCEPT_LANGUAGE_VARIANTS = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
]
CACHE_CONTROL_VARIANTS = [
    "max-age=0",
    "no-cache",
    "max-age=300",
]
CONNECTION_VARIANTS = ["keep-alive", "close"]


def get_header_variation() -> Dict[str, str]:
    """Return slightly varied request headers (Accept-Language, Cache-Control, Connection)."""
    return {
        "Accept-Language": random.choice(ACCEPT_LANGUAGE_VARIANTS),
        "Cache-Control": random.choice(CACHE_CONTROL_VARIANTS),
        "Connection": random.choice(CONNECTION_VARIANTS),
    }


def get_headers_for_request(include_user_agent: bool = True) -> Dict[str, str]:
    """Return full set of varied headers; optionally include randomized User-Agent."""
    out = get_header_variation()
    if include_user_agent:
        out["User-Agent"] = get_random_user_agent()
    return out


def header_variation_status() -> Dict[str, Any]:
    """Return status of header variation."""
    h = get_header_variation()
    return {
        "Accept-Language": h.get("Accept-Language"),
        "Cache-Control": h.get("Cache-Control"),
        "Connection": h.get("Connection"),
        "status": STATUS_OK,
    }


# --- 4) Request jitter ---
DEFAULT_BASE_DELAY = 1.0
DEFAULT_JITTER_MAX = 2.0


def get_request_jitter_delay(
    base_delay: float = DEFAULT_BASE_DELAY,
    jitter_max: float = DEFAULT_JITTER_MAX,
) -> float:
    """Return delay in seconds: base_delay + random jitter in [0, jitter_max]."""
    return base_delay + random.uniform(0, jitter_max)


def request_jitter_status() -> Dict[str, Any]:
    """Return status and a sample delay."""
    delay = get_request_jitter_delay()
    return {
        "base_delay": DEFAULT_BASE_DELAY,
        "jitter_max": DEFAULT_JITTER_MAX,
        "sample_delay_seconds": round(delay, 2),
        "status": STATUS_OK,
    }


# --- 5) Navigation pattern simulation ---
NAV_STEP_SEARCH = "search"
NAV_STEP_PRODUCT = "product_page"
NAV_STEP_BACK = "back_to_search"

DEFAULT_PATTERN: List[str] = [NAV_STEP_SEARCH, NAV_STEP_PRODUCT, NAV_STEP_BACK]

_nav_index: int = 0


def get_navigation_pattern() -> List[str]:
    """Return the human-like browsing sequence (search → product → back to search)."""
    return list(DEFAULT_PATTERN)


def get_next_navigation_step() -> str:
    """Return next suggested step in the pattern; cycles."""
    global _nav_index
    pattern = get_navigation_pattern()
    step = pattern[_nav_index % len(pattern)]
    _nav_index += 1
    return step


def navigation_pattern_simulation_status() -> Dict[str, Any]:
    """Return status (pattern, next step)."""
    return {
        "pattern": get_navigation_pattern(),
        "next_step": get_next_navigation_step(),
        "status": STATUS_OK,
    }


# --- 6) Captcha detection ---
def _is_captcha_or_block(html: str) -> bool:
    """Heuristic: captcha or block page."""
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


def captcha_detection(html: Optional[str] = None, url: Optional[str] = None) -> Dict[str, Any]:
    """Detect captcha or block pages. Returns detected (bool), reason (str)."""
    if html is None or not isinstance(html, str):
        return {"detected": False, "reason": "no_content", "status": STATUS_OK}
    if _is_captcha_or_block(html):
        return {"detected": True, "reason": "captcha_or_block", "status": STATUS_OK}
    return {"detected": False, "reason": "ok", "status": STATUS_OK}


# --- 7) Block response classifier ---
CLASS_CAPTCHA = "captcha_page"
CLASS_BOT_DETECTION = "bot_detection_page"
CLASS_UNUSUAL_REDIRECT = "unusual_redirect"
CLASS_OK = "ok"


def block_response_classifier(
    html: Optional[str] = None,
    url: Optional[str] = None,
    final_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Classify response: captcha_page, bot_detection_page, unusual_redirect, or ok.
    unusual_redirect: when final_url differs significantly from requested url (e.g. login/captcha path).
    """
    result: Dict[str, Any] = {
        "classification": CLASS_OK,
        "reason": "ok",
        "status": STATUS_OK,
    }
    if not html or not isinstance(html, str):
        return result
    lower = html.lower()
    if "captcha" in lower or "unusual traffic" in lower:
        result["classification"] = CLASS_CAPTCHA
        result["reason"] = "captcha_page"
        return result
    if "robot" in lower or "bot detection" in lower or "automated access" in lower:
        result["classification"] = CLASS_BOT_DETECTION
        result["reason"] = "bot_detection_page"
        return result
    if "blocked" in lower and "access" in lower:
        result["classification"] = CLASS_BOT_DETECTION
        result["reason"] = "blocked_access"
        return result
    if final_url and url and str(final_url).strip() != str(url).strip():
        # Simple heuristic: redirect to captcha/login-like path
        fu = str(final_url).lower()
        if "captcha" in fu or "robot" in fu or "blocked" in fu or "verify" in fu:
            result["classification"] = CLASS_UNUSUAL_REDIRECT
            result["reason"] = "unusual_redirect"
            return result
    return result


# --- Aggregate status ---
def get_antibot_status() -> Dict[str, Any]:
    """Return output structure: anti_bot_status, session_rotation, header_randomization, request_jitter, captcha_detection."""
    return {
        "anti_bot_status": STATUS_OK,
        "session_rotation": session_rotation_manager_status().get("status", STATUS_OK),
        "header_randomization": header_variation_status().get("status", STATUS_OK),
        "request_jitter": request_jitter_status().get("status", STATUS_OK),
        "captcha_detection": STATUS_OK,
    }
