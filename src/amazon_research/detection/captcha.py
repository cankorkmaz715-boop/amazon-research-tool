"""
Lightweight CAPTCHA / bot-check detection (Step 32). No solving; callers abort and persist.
"""
import re
from typing import Optional

from amazon_research.logging_config import get_logger

logger = get_logger("detection.captcha")

# Patterns that indicate CAPTCHA or robot check (Amazon and similar). Keep compact.
_CAPTCHA_PATTERNS = [
    re.compile(r"robot\s*check", re.I),
    re.compile(r"enter the characters you see", re.I),
    re.compile(r"make sure you're not a robot", re.I),
    re.compile(r"captcha", re.I),
    re.compile(r"unusual traffic", re.I),
    re.compile(r"automated access", re.I),
]
_URL_CAPTCHA = re.compile(r"captcha|robot|blocked", re.I)


def is_captcha_or_bot_check_content(
    url: str = "",
    title: str = "",
    body_text: str = "",
) -> bool:
    """
    Pure check: return True if url/title/body_text indicate CAPTCHA or bot-check.
    Use this from tests or when you have content without a Playwright page.
    """
    url = url or ""
    title = (title or "")[:500]
    body_text = (body_text or "")[:2000]
    if _URL_CAPTCHA.search(url):
        return True
    if any(p.search(title) for p in _CAPTCHA_PATTERNS):
        return True
    if any(p.search(body_text) for p in _CAPTCHA_PATTERNS):
        return True
    return False


def is_captcha_or_bot_check(page) -> bool:
    """
    Return True if the current page looks like a CAPTCHA or bot-check. Lightweight; no solving.
    Uses sync Playwright page; call only from sync context (e.g. bots).
    """
    try:
        url = page.url
        title = (page.title() or "")[:500]
        body = page.evaluate("() => document.body ? document.body.innerText.slice(0, 2000) : ''") or ""
        return is_captcha_or_bot_check_content(url=url, title=title, body_text=body)
    except Exception as e:
        logger.debug("captcha check failed: %s", e)
    return False
