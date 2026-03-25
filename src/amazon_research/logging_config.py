"""
Central logging setup. One place for format, level, and handlers.
Structured logs (JSON) for production; console for local dev.
"""
import logging
import sys
from typing import Optional

from .config import get_config


def setup_logging(
    level: Optional[str] = None,
    format_type: Optional[str] = None,
) -> None:
    """Configure root logger. Call once at application startup."""
    try:
        cfg = get_config()
        level = level or cfg.log_level
        format_type = format_type or cfg.log_format
    except Exception:
        level = level or "INFO"
        format_type = format_type or "console"

    root = logging.getLogger("amazon_research")
    root.setLevel(level.upper())
    root.handlers.clear()

    if format_type == "json":
        try:
            from pythonjsonlogger import jsonlogger
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(jsonlogger.JsonFormatter())
            root.addHandler(handler)
        except ImportError:
            _fallback_console(root, level)
    else:
        _fallback_console(root, level)


def _fallback_console(root: logging.Logger, level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level.upper())
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for module `name`. Use this instead of logging.getLogger."""
    return logging.getLogger(f"amazon_research.{name}")
