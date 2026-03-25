"""
Lightweight detection (CAPTCHA, bot-check). No solving; abort and persist failure reason.
"""

from .captcha import is_captcha_or_bot_check

__all__ = ["is_captcha_or_bot_check"]
